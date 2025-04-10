// Copyright (c) 2025 ETH Zurich.
//                    All rights reserved.
//
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// Main authors: Lorenzo Paleari

"use client";

import { ReactNode, useEffect, useState } from "react";
import DropArea from "@/src/app/components/dropArea";
import Overlay from "@/src/app/components/overlay";
import LoadingBar from "@/src/app/components/loadingBar";
import Image from "next/image";

export default function Home() {
  const [file, setFile] = useState<File[]>([]);
  const [isOverlayOpen, setIsOverlayOpen] = useState(false);
  const [overlayContent, setOverlayContent] = useState<ReactNode | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [totalFiles, setTotalFiles] = useState(0);
  const [loadedFiles, setLoadedFiles] = useState(0);
  const [dropAreaText, setDropAreaText] = useState("");
  const [openNewTab, setOpenNewTab] = useState(false);

  useEffect(() => {
    if (openNewTab) {
      const newTab = window.open(
        `http://${process.env.NEXT_PUBLIC_NEO4J_EXTERNAL_HOST}:${process.env.NEXT_PUBLIC_NEO4J_HTTP_PORT}/browser?dbms=neo4j://${process.env.NEXT_PUBLIC_NEO4J_EXTERNAL_HOST}:${process.env.NEXT_PUBLIC_NEO4J_BOLT_PORT}&preselectAuthMethod=NO_AUTH`,
        "_blank"
      );
      if (newTab) {
        newTab.focus();
      } else {
        alert("Failed to open new tab. Please allow pop-ups for this site.");
      }

      setOpenNewTab(false);
    }
    // Cleanup function (optional)
    return () => {
      // Any cleanup code, if needed
    };
  }, [openNewTab]);

  const toggleOverlay = () => {
    setIsOverlayOpen(!isOverlayOpen);
  };

  // Function to pass the data to the backend and load the graph on Neo4j
  const load_graph = async () => {
    if (file.length === 0) {
      setOverlayContent(
        <div>
          <h2 className="text-xl font-bold text-center mb-4">
            No files selected
          </h2>
          <p className="text-center">
            Please select at least one file to upload.
          </p>
        </div>
      );
      toggleOverlay();
      return;
    }

    setIsLoading(true);
    setTotalFiles(file.length);
    setLoadedFiles(0);

    const readFile = (file: File): Promise<string> => {
      return new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (event) => {
          const fileContent = event.target?.result;
          if (typeof fileContent === "string") {
            resolve(fileContent);
          } else {
            reject("File content is not a string");
          }
        };
        reader.onerror = reject;
        reader.readAsText(file);
      });
    };

    const uploadFile = async (fileContent: string, index: number) => {
      const response = await fetch("/api/load_graph", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        cache: "no-store",
        body: JSON.stringify({
          json_data: fileContent,
          file_name: file[index].name,
        }),
      });
      return response.json();
    };

    try {
      const promises = file.map(async (f, index) => {
        const fileContent = await readFile(f);
        const result = await uploadFile(fileContent, index);
        setLoadedFiles((prev) => prev + 1);
        return result;
      });

      const results = await Promise.all(promises);
      for (const result of results) {
        if (result.message != "success") {
          setDropAreaText("Error uploading files");
          console.error("Error uploading files:", result);
          setIsLoading(false);
          return;
        }
      }
      setDropAreaText("All files uploaded successfully");
      console.log("Results:", results);
      setFile([]);
      setIsLoading(false);
      setOpenNewTab(true);
    } catch (error) {
      setDropAreaText("Error uploading files");
      console.error("Error uploading files:", error);
      setIsLoading(false);
    }
  };

  //function to wipe out the dbms
  const reset_dbms = async () => {
    const response = await fetch("/api/reset", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });
    const data = await response.json();
    if (data.message === "success") {
      setDropAreaText("DBMS reset successfully");
    } else {
      setDropAreaText("Error resetting DBMS");
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-12 gap-5 overflow-auto">
      <div className="flex flex-col items-center justify-center gap-10">
        <h1 className="text-4xl font-bold text-center">
          Welcome to the Visualization Tool
        </h1>
        <div className="flex flex-col w-full items-center justify-center gap-4">
          <h2 className="text-2xl font-bold text-center">Instructions</h2>
          <div className="flex flex-col w-full items-center justify-center gap-1">
            <p className="text-md font-normal w-[500px]">
              1. Upload the desired json Snapshots. And click on the button.
            </p>
            <p className="text-md font-normal w-[500px]">
              2. At successful upload, the Neo4j browser will open in a new tab.
            </p>
            <p className="text-md font-normal w-[500px]">
              3. The browser will connect automatically to the Neo4j database.
            </p>
            <p className="text-md flex flex-row font-normal w-[500px]">
              4. At successful connection, click on the following icon (top-left
              corner)
              <Image src="/db.png" alt="Database png" width={50} height={50} />
            </p>
            <p className="text-md font-normal w-[500px]">
              5. Click on any Node Label to view the corresponding nodes. Every
              label correspond to a different snapshot of the data easily
              recognizable by the name.
            </p>
          </div>
        </div>
      </div>
      <DropArea
        file={file}
        setFile={setFile}
        dropAreaText={dropAreaText}
        setDropAreaText={setDropAreaText}
      />
      <LoadingBar
        isLoading={isLoading}
        totalFiles={totalFiles}
        loadedFiles={loadedFiles}
      />
      <div className="flex flex-row gap-4">
        <button
          className="mt-8 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          onClick={load_graph}
        >
          Load Data
        </button>
        <button
          className="mt-8 bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
          onClick={reset_dbms}
        >
          Reset Neo4j
        </button>
      </div>
      {isOverlayOpen && (
        <Overlay onClose={toggleOverlay}>{overlayContent}</Overlay>
      )}
    </main>
  );
}
