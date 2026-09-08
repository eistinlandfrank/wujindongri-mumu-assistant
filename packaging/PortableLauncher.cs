using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("WJDR MuMu Assistant Portable")]
[assembly: AssemblyVersion("5.66.0.0")]
[assembly: AssemblyFileVersion("5.66.0.0")]

internal static class PortableLauncher
{
    static string Hash(Stream stream) {
        using (SHA256 sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "");
    }
    static string FileHash(string path) {
        if (!File.Exists(path)) return "";
        using (Stream input=File.OpenRead(path)) return Hash(input);
    }
    static Stream Resource(string name) {
        Stream value=Assembly.GetExecutingAssembly().GetManifestResourceStream(name);
        if(value==null) throw new InvalidDataException("缺少便携资源："+name);
        return value;
    }
    static string TextResource(string name) {
        using(StreamReader reader=new StreamReader(Resource(name))) return reader.ReadToEnd().Trim();
    }
    static string SafePath(string root,string relative) {
        string target=Path.GetFullPath(Path.Combine(root,relative.Replace('/',Path.DirectorySeparatorChar)));
        if(!target.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("便携包包含无效路径");
        return target;
    }
    static int Run(bool verifyOnly,Action<string> status) {
        string digest=TextResource("payload.sha256");
        string root=Path.GetFullPath(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "WJDRMuMuAssistant","portable","5.66.0-"+digest.Substring(0,12)));
        using(Mutex mutex=new Mutex(false,"Local\\WJDR-Portable-"+digest.Substring(0,12))) {
            bool acquired=false;
            try {
                try { acquired=mutex.WaitOne(10000); } catch(AbandonedMutexException) { acquired=true; }
                if(!acquired) throw new TimeoutException("另一个便携启动器正在准备，请稍后重试");
                status("正在校验离线便携包…");
                using(Stream data=Resource("payload.zip"))
                    if(Hash(data)!=digest) throw new InvalidDataException("便携包 SHA256 校验失败");
                Directory.CreateDirectory(root);
                string[] manifest=TextResource("files.sha256").Split(new[]{'\n'},StringSplitOptions.RemoveEmptyEntries);
                bool valid=true;
                foreach(string line in manifest) {
                    string[] fields=line.TrimEnd('\r').Split('\t');
                    if(fields.Length!=2 || FileHash(SafePath(root,fields[1]))!=fields[0]) {valid=false;break;}
                }
                if(!valid) {
                    status("首次运行：正在解压，无需安装…");
                    using(Stream data=Resource("payload.zip"))
                    using(ZipArchive zip=new ZipArchive(data,ZipArchiveMode.Read)) {
                        foreach(ZipArchiveEntry entry in zip.Entries) {
                            string output=SafePath(root,entry.FullName);
                            if(entry.FullName.EndsWith("/")) {Directory.CreateDirectory(output);continue;}
                            Directory.CreateDirectory(Path.GetDirectoryName(output));
                            using(Stream input=entry.Open())
                            using(Stream target=File.Create(output)) input.CopyTo(target);
                        }
                    }
                }
                foreach(string line in manifest) {
                    string[] fields=line.TrimEnd('\r').Split('\t');
                    if(fields.Length!=2 || FileHash(SafePath(root,fields[1]))!=fields[0])
                        throw new InvalidDataException("运行文件校验失败");
                }
                File.WriteAllText(Path.Combine(root,"portable-verification.log"),DateTime.UtcNow.ToString("o")+" SHA256 verified\n");
                if(!verifyOnly) {
                    status("校验通过，正在打开无尽冬日助手…");
                    Process.Start(new ProcessStartInfo(Path.Combine(root,"WJDRMuMuAssistant.exe")) {
                        WorkingDirectory=root,UseShellExecute=false
                    });
                }
                return 0;
            } finally { if(acquired) mutex.ReleaseMutex(); }
        }
    }
    [STAThread]
    static int Main(string[] args) {
        bool verifyOnly=Array.IndexOf(args,"--verify-only")>=0;
        using(System.Threading.Timer guard=new System.Threading.Timer(_=>Environment.Exit(124),null,30000,Timeout.Infinite)) {
            if(verifyOnly) { try{return Run(true,_=>{});}catch{return 1;} }
            Application.EnableVisualStyles();
            Form form=new Form {Text="无尽冬日助手 5.66.0 · 免安装",Width=450,Height=145,
                StartPosition=FormStartPosition.CenterScreen,FormBorderStyle=FormBorderStyle.FixedDialog,MaximizeBox=false};
            Label label=new Label {Left=22,Top=20,Width=405,Height=28,Text="正在准备便携运行环境…"};
            ProgressBar progress=new ProgressBar {Left=22,Top=58,Width=390,Style=ProgressBarStyle.Marquee};
            form.Controls.Add(label);form.Controls.Add(progress);
            int result=1;
            form.Shown+=(sender,evt)=>ThreadPool.QueueUserWorkItem(_=> {
                try { result=Run(false,text=>form.BeginInvoke((Action)(()=>label.Text=text))); }
                catch(Exception ex) { form.Invoke((Action)(()=>MessageBox.Show(form,ex.Message,"便携启动失败"))); }
                finally { form.BeginInvoke((Action)(()=>form.Close())); }
            });
            Application.Run(form);
            return result;
        }
    }
}
