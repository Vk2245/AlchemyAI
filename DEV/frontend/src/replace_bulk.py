import re

with open('C:\\VK224\\Projects\\Alchemy AI\\Project\\UNI-HACK\\DEV\\frontend\\src\\components\\BulkExcelUpload.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the state variables to remove progress and message, add abortControllerRef
new_state = '''  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const router = useRouter();'''

content = re.sub(
    r'  const \[isUploading, setIsUploading\] = useState\(false\);\n  const \[progress, setProgress\] = useState\(0\);\n  const \[message, setMessage\] = useState\(""\);\n  const \[error, setError\] = useState<string \| null>\(null\);\n\n  const fileInputRef = useRef<HTMLInputElement>\(null\);\n  const router = useRouter\(\);',
    new_state,
    content
)


# Replace startUploadAndProcess completely
old_upload_start = "  const startUploadAndProcess = async () => {"
old_upload_end = "  return ("

new_upload = '''  const startUploadAndProcess = async () => {
    if (!file || disabled) return;
    setIsUploading(true);
    setError(null);
    if (onUploadStart) onUploadStart();

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        setError("You must be logged in.");
        setTimeout(() => router.push("/login"), 1500);
        if (onUploadEnd) onUploadEnd();
        return;
      }

      const formData = new FormData();
      formData.append("file", file);

      const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      
      const res = await fetch(${API}/api/upload, {
        method: "POST",
        headers: {
          "Authorization": Bearer 
        },
        body: formData,
        signal: abortController.signal,
      });

      if (!res.ok) throw new Error(Upload failed ());
      const data = await res.json();
      
      // Clean up the name for the URL slug
      const safeName = file.name.replace(/[^a-zA-Z0-9.-]/g, "_").replace(/\.(xlsx|csv)$/i, "");
      router.push(/process/-);
      if (onUploadEnd) onUploadEnd();
      
    } catch (err: any) {
      if (err.name === "AbortError") {
        setError("Upload cancelled.");
      } else {
        setError(err.message || "Unexpected error.");
      }
      setIsUploading(false);
      if (onUploadEnd) onUploadEnd();
    }
  };

'''

content = content[:content.find(old_upload_start)] + new_upload + content[content.find(old_upload_end):]

# Update the UI section to remove the progress bar and add the spinner
old_ui_start = "{isUploading ? ("
old_ui_end = "              </motion.div>"

new_ui = '''{isUploading ? (
                  <div className="flex gap-3 w-full max-w-xs">
                    <button
                      onClick={() => {
                        if (isUploading && abortControllerRef.current) {
                          abortControllerRef.current.abort();
                        }
                        setFile(null);
                        setError(null);
                        setIsUploading(false);
                      }}
                      disabled={disabled}
                      className="flex-1 btn-ghost text-sm px-4 py-2.5 rounded-xl disabled:opacity-40"
                    >
                      Cancel
                    </button>
                    <button
                      disabled={true}
                      className="flex-[2] btn-primary text-sm px-4 py-2.5 rounded-xl flex items-center justify-center gap-2 disabled:opacity-40 disabled:hover:scale-100"
                    >
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{
                          repeat: Infinity,
                          duration: 0.8,
                          ease: "linear",
                        }}
                        className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full"
                      />
                    </button>
                  </div>
                ) : (
                  <div className="flex gap-3 w-full max-w-xs">
                    <button
                      onClick={() => {
                        setFile(null);
                        setError(null);
                      }}
                      disabled={isUploading || disabled}
                      className="flex-1 btn-ghost text-sm px-4 py-2.5 rounded-xl disabled:opacity-40"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={startUploadAndProcess}
                      disabled={isUploading || disabled}
                      className="flex-[2] btn-primary text-sm px-4 py-2.5 rounded-xl flex items-center justify-center gap-2 disabled:opacity-40 disabled:hover:scale-100"
                    >
                      Start <ArrowRight size={14} />
                    </button>
                  </div>
                )}
              </motion.div>'''

content = content[:content.find(old_ui_start)] + new_ui + content[content.find(old_ui_end) + 27:]

with open('C:\\VK224\\Projects\\Alchemy AI\\Project\\UNI-HACK\\DEV\\frontend\\src\\components\\BulkExcelUpload.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced BulkExcelUpload logic")
