// Copyright (c) 2025 ETH Zurich.
//                    All rights reserved.
//
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// Main authors: Lorenzo Paleari

import React from "react";

import { FaTimes } from "react-icons/fa"; // Import react-icons for the red cross
import { FileUploader } from "react-drag-drop-files";

const fileTypes = ["JSON"];

export default function DropArea({
  file,
  setFile,
  dropAreaText,
  setDropAreaText,
}: {
  file: File[];
  setFile: (file: File[]) => void;
  dropAreaText: string;
  setDropAreaText: (text: string) => void;
}) {
  const handleChange = (newFile: File[]) => {
    setFile([...file, ...newFile]);
    setDropAreaText("");
  };

  const handleRemove = (index: number) => {
    const newFiles = [...file];
    newFiles.splice(index, 1);
    setFile(newFiles);
  };

  return (
    <div className="flex flex-col justify-center items-center gap-4">
      <div className="w-full flex flex-row items-center justify-center">
        <FileUploader
          handleChange={handleChange}
          multiple={true}
          fileOrFiles={file}
          name="file"
          types={fileTypes}
        >
          <div className="w-full flex flex-col items-center hover:cursor-pointer">
            <div className="border-2 border-dashed border-gray-400 p-10 w-full text-center rounded-md cursor-pointer hover:bg-gray-100 transition">
              {file.length > 0
                ? "Add new files"
                : "Drop your files here or click to upload"}
            </div>
          </div>
        </FileUploader>
        <div className="flex flex-col">
          {file.length > 0 && (
            <ul className="pl-5">
              {file.map((f, index) => (
                <li
                  key={index}
                  className="flex justify-between items-center my-2"
                >
                  <span className="text-black">{f.name}</span>
                  <button
                    className="ml-2 text-red-500 hover:text-red-700"
                    onClick={() => handleRemove(index)}
                  >
                    <FaTimes />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="w-full text-center">
        <p className="text-black">{dropAreaText}</p>
      </div>
    </div>
  );
}
