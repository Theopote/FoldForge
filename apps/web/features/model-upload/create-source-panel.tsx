"use client";

import { useEffect } from "react";
import { ImageIcon, Type, Upload } from "lucide-react";
import { useSearchParams } from "next/navigation";

import { ImageToModelPanel } from "@/features/model-upload/image-to-model-panel";
import { ModelUploadPanel } from "@/features/model-upload/model-upload-panel";
import { TextToModelPanel } from "@/features/model-upload/text-to-model-panel";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { SourceType } from "@/types";
import { useStudioStore } from "@/store/studio-store";

export function CreateSourcePanel() {
  const searchParams = useSearchParams();
  const { sourceType, setSourceType } = useStudioStore();
  const sampleId = searchParams.get("sample");
  const promptCaseId = searchParams.get("promptCase");

  useEffect(() => {
    if (sampleId && sourceType !== "upload_3d") {
      setSourceType("upload_3d");
      return;
    }
    if (promptCaseId && sourceType !== "text_to_3d") {
      setSourceType("text_to_3d");
    }
  }, [promptCaseId, sampleId, setSourceType, sourceType]);

  return (
    <Tabs
      value={sourceType}
      onValueChange={(value) => setSourceType(value as SourceType)}
    >
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="upload_3d" className="gap-1">
          <Upload className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Upload</span>
        </TabsTrigger>
        <TabsTrigger value="text_to_3d" className="gap-1">
          <Type className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Text</span>
        </TabsTrigger>
        <TabsTrigger value="image_to_3d" className="gap-1">
          <ImageIcon className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Image</span>
        </TabsTrigger>
      </TabsList>

      <TabsContent value="upload_3d">
        <ModelUploadPanel />
      </TabsContent>
      <TabsContent value="text_to_3d">
        <TextToModelPanel />
      </TabsContent>
      <TabsContent value="image_to_3d">
        <ImageToModelPanel />
      </TabsContent>
    </Tabs>
  );
}
