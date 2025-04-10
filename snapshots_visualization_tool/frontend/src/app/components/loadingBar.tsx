// Copyright (c) 2025 ETH Zurich.
//                    All rights reserved.
//
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// Main authors: Lorenzo Paleari

import { useEffect, useState } from "react";

interface LoadingBarProps {
  isLoading: boolean;
  totalFiles: number;
  loadedFiles: number;
}

const LoadingBar: React.FC<LoadingBarProps> = ({
  isLoading,
  totalFiles,
  loadedFiles,
}) => {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (isLoading) {
      setProgress((loadedFiles / totalFiles) * 100);
    }
  }, [isLoading, totalFiles, loadedFiles]);

  return (
    <div className="w-full mx-auto flex items-center justify-center mt-4">
      {isLoading && (
        <div className="w-[400px] h-4 bg-gray-200 rounded-full relative overflow-hidden">
          <div
            className="absolute top-0 right-0 h-full w-full bg-blue-500 opacity-75 animate-moving-bar"
            style={{ width: `${100 - progress}%` }}
          ></div>
          <div
            className="absolute top-0 left-0 h-full bg-blue-500 text-xs font-medium text-blue-100 text-center leading-none rounded-full"
            style={{ width: `${progress}%` }}
          ></div>
          <div className="absolute top-0 left-0 h-full w-full flex items-center justify-center overflow-hidden">
            <span className="text-black">
              {loadedFiles} / {totalFiles} files loaded
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoadingBar;
