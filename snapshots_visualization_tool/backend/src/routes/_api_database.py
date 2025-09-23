# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari

import time

from database import dbms_reset_neo4j, get_max_id, import_graph_from_json
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel


class _API_DATABASE:
    def __init__(self, app: FastAPI) -> None:
        router = APIRouter()
        self.max_id = 0
        self.semaphore = False

        class jsonContent(BaseModel):
            content: str
            name: str

        @router.post("/load_graph")
        def load_graph(params: jsonContent):
            while self.semaphore:
                time.sleep(1)
            self.semaphore = True

            json_content = params.content
            name = params.name.replace(".", " ").replace(" ", "_").replace("-", "_").replace("/", "_").replace("\\", "_").replace(":", "_").replace(";", "_").replace("?", "_").replace("!", "_").replace(",", "_").replace("(", "_").replace(")", "_").replace("[", "_").replace("]", "_").replace("json", "")
            
            # Change all id parameters adding the max_id to ensure that the ids are unique
            max_id_json = 0
            min_id_json = 999999999
            for line in json_content.split("\n"):
                if "id" in line:
                    id_index = line.find("id")
                    next_comma = line.find(",", id_index)
                    line_piece = line[id_index:next_comma]
                    id_value = int(line_piece.split(":")[1].replace(",", "").replace('"', ""))
                    if id_value > max_id_json:
                        max_id_json = id_value
                    if id_value < min_id_json:
                        min_id_json = id_value
            
            self.max_id = get_max_id()
            # Change all id parameters adding the max_id starting from max_id to min_id using replace
            for i in range(max_id_json, min_id_json-1, -1):
                json_content = json_content.replace(f'"id":"{i}"', f'"id":"{i+self.max_id}"')
            
            with open("/import/files/temp.json", "w") as f:
                f.write(json_content)
            f.close()

            result = import_graph_from_json("/import/files/temp.json", name)

            if result:
                self.max_id = get_max_id()
                self.semaphore = False
                return {"edge_label": f"{name}"}
            else:
                self.semaphore = False
                raise HTTPException(status_code=400, detail="Error loading graph from JSON.")
            
        @router.post("/reset_dbms")
        async def reset_neo4j():
            # Command to delete every relationship, node, label and schema in the database 
            result = dbms_reset_neo4j()

            if result:
                return {"message": "success"}
            else:
                self.semaphore = False
                raise HTTPException(status_code=400, detail="Error loading graph from JSON.")

        app.include_router(router)
