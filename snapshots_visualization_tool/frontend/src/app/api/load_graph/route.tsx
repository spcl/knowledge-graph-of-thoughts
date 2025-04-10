// Copyright (c) 2025 ETH Zurich.
//                    All rights reserved.

// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Main authors: Lorenzo Paleari

"use server";

import { NextResponse } from "next/server";

export async function POST(request: Request) {
  let edge_label = "";
  try {
    const { json_data, file_name } = await request.json();
    const answer = await fetch(process.env.API_URL + "/load_graph", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
      body: JSON.stringify({
        content: json_data,
        name: file_name,
      }),
    });
    if (answer.status === 200) {
      const data = await answer.json();
      edge_label = data.edge_label;
    } else {
      return NextResponse.json({ message: "error" });
    }
  } catch (e) {
    return NextResponse.json({ message: "failed" });
  }

  return NextResponse.json({
    message: "success",
    edge_label: edge_label,
  });
}
