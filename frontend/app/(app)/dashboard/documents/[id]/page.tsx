"use client";
import dynamic from "next/dynamic";
import { Spinner } from "@/components/app/Spinner";

const DocumentEditorComponent = dynamic(
  () => import("@/components/app/DocumentEditor"),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-64">
        <Spinner className="w-5 h-5" />
      </div>
    ),
  }
);

export default function DocumentEditorPage({
  params,
}: {
  params: { id: string };
}) {
  const id = params.id;

  if (!id || id === "undefined") {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner className="w-5 h-5" />
      </div>
    );
  }

  return <DocumentEditorComponent docId={id} />;
}