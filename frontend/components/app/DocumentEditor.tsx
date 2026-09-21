"use client";
import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import api from "@/lib/api";
import { Document } from "@/types";
import { Spinner } from "@/components/app/Spinner";
import { ArrowLeft, Check } from "lucide-react";

export default function DocumentEditor({ docId }: { docId: string }) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [saved, setSaved] = useState(true);
  const [saveTimer, setSaveTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

  // ALL hooks must come before any early return
  const { data: doc, isLoading } = useQuery<Document>({
    queryKey: ["document", docId],
    queryFn: () => api.get(`/documents/${docId}`).then(r => r.data),
    enabled: !!docId && docId !== "undefined", // safe guard
  });

  const updateMutation = useMutation({
    mutationFn: (data: { title?: string; content?: string }) =>
      api.patch(`/documents/${docId}`, data),
    onSuccess: () => setSaved(true),
  });

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder: "Start writing... The AI will learn from this document automatically.",
      }),
    ],
    immediatelyRender: false,
    content: "",
    editorProps: { attributes: { class: "ProseMirror" } },
    onUpdate: ({ editor }) => {
      setSaved(false);
      if (saveTimer) clearTimeout(saveTimer);
      const t = setTimeout(() => {
        updateMutation.mutate({ content: editor.getText() });
      }, 1500);
      setSaveTimer(t);
    },
  });

  useEffect(() => {
    if (doc) {
      setTitle(doc.title);
      if (editor && doc.content && editor.isEmpty) {
        editor.commands.setContent(doc.content);
      }
    }
  }, [doc, editor]);

  const handleTitleBlur = () => {
    if (title !== doc?.title) {
      setSaved(false);
      updateMutation.mutate({ title });
    }
  };

  // Early returns AFTER all hooks
  if (!docId || docId === "undefined") {
    return <div className="flex items-center justify-center h-64"><Spinner className="w-5 h-5" /></div>;
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><Spinner className="w-5 h-5" /></div>;
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <div className="flex items-center gap-3 mb-8 animate-fade-up">
        <button onClick={() => router.back()} className="orbit-btn-ghost text-xs py-1.5 px-3">
          <ArrowLeft className="w-3.5 h-3.5" /> Back
        </button>
        <div className="flex-1" />
        <div className={`flex items-center gap-1.5 text-[11px] font-mono transition-colors duration-300 ${saved ? "text-accent" : "text-[#5a5a7a]"}`}>
          {saved
            ? <><Check className="w-3 h-3" /> Saved</>
            : <><Spinner className="w-3 h-3" /> Saving...</>
          }
        </div>
      </div>

      <div className="animate-[fadeUp_0.5s_0.05s_ease_both]">
        <input
          value={title}
          onChange={e => { setTitle(e.target.value); setSaved(false); }}
          onBlur={handleTitleBlur}
          placeholder="Untitled"
          className="w-full bg-transparent border-none outline-none font-display font-extrabold text-[#e8e8f0] tracking-tight mb-4 placeholder-[#3a3a5a]"
          style={{ fontSize: "clamp(1.6rem, 4vw, 2.2rem)" }}
        />
        <div className="w-10 h-0.5 bg-accent opacity-40 mb-6" />
      </div>

      <div className="animate-[fadeUp_0.5s_0.1s_ease_both]">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}