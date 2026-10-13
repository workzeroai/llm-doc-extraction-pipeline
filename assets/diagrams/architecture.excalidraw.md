---
excalidraw-plugin: parsed
tags: [excalidraw]
---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==
# Drawing
```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin/releases/tag/2.0.0",
  "elements": [
    {
      "id": "zone-providers",
      "type": "rectangle",
      "x": 890,
      "y": 235.0,
      "width": 280,
      "height": 452.0,
      "angle": 0,
      "strokeColor": "#6d28d9",
      "backgroundColor": "#f8fafc",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "dashed",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "seed": 624998864,
      "version": 1,
      "versionNonce": 253889399,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false
    },
    {
      "id": "zone-providers-label",
      "type": "text",
      "x": 906,
      "y": 245.0,
      "width": 181.0,
      "height": 20.0,
      "angle": 0,
      "strokeColor": "#6d28d9",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 381895648,
      "version": 1,
      "versionNonce": 299479748,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "providers — 같은 출력 모양",
      "fontSize": 16,
      "fontFamily": 2,
      "textAlign": "left",
      "verticalAlign": "top",
      "baseline": 13.12,
      "containerId": null,
      "originalText": "providers — 같은 출력 모양",
      "lineHeight": 1.25
    },
    {
      "id": "node-docgen",
      "type": "rectangle",
      "x": 0,
      "y": 97.0,
      "width": 180,
      "height": 120,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "#f1f5f9",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "seed": 617820959,
      "version": 1,
      "versionNonce": 108330532,
      "isDeleted": false,
      "boundElements": [
        {
          "type": "text",
          "id": "text-docgen"
        },
        {
          "type": "arrow",
          "id": "edge-docgen-pdftext-0"
        }
      ],
      "updated": 1760000000000,
      "link": null,
      "locked": false
    },
    {
      "id": "node-pdftext",
      "type": "rectangle",
      "x": 320,
      "y": 97.0,
      "width": 180,
      "height": 100,
      "angle": 0,
      "strokeColor": "#0369a1",
      "backgroundColor": "#e0f2fe",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "seed": 1462827501,
      "version": 1,
      "versionNonce": 1703737786,
      "isDeleted": false,
      "boundElements": [
        {
          "type": "text",
          "id": "text-pdftext"
        },
        {
          "type": "arrow",
          "id": "edge-docgen-pdftext-0"
        },
        {
          "type": "arrow",
          "id": "edge-pdftext-classify-1"
        }
      ],
      "updated": 1760000000000,
      "link": null,
      "locked": false
    },
    {
      "id": "node-classify",
      "type": "rectangle",
      "x": 580,
      "y": 97.0,
      "width": 180,
      "height": 120,
      "angle": 0,
      "strokeColor": "#0369a1",
      "backgroundColor": "#e0f2fe",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "seed": 1251205652,
      "version": 1,
      "versionNonce": 630189796,
      "isDeleted": false,
      "boundElements": [
        {
          "type": "text",
          "id": "text-classify"
        },
        {
          "type": "arrow",
          "id": "edge-pdftext-classify-1"
        },
        {
          "type": "arrow",
          "id": "edge-classify-extract-2"
        },
        {
          "type": "arrow",
          "id": "edge-schemas-classify-6"
        }
      ],
      "updated": 1760000000000,
      "link": null,
      "locked": false
    },
    {
      "id": "node-extract",
      "type": "rectangle",
      "x": 920,
      "y": 97.0,
      "width": 220,
      "height": 100,
      "angle": 0,
      "strokeColor": "#6d28d9",
      "backgroundColor": "#ede9fe",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "seed": 678209063,
      "version": 1,
      "versionNonce": 762056306,
      "isDeleted": false,
      "boundElements": [
        {
          "type": "text",
          "id": "text-extract"
        },
        {
          "type": "arrow",
          "id": "edge-classify-extract-2"
        },
        {
          "type": "arrow",
          "id": "edge-extract-validate-3"
        }
      ],
      "updated": 1760000000000,
      "link": null,
      "locked": false
    },
    {
      "id": "node-schemas",
      "type": "rectangle",
      "x": 580,
      "y": 297.0,
      "width": 200,
      "height": 120,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "#f1f5f9",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "seed": 1760868917,
      "version": 1,
      "versionNonce": 612042967,
      "isDeleted": false,
      "boundElements": [
        {
          "type": "text",
          "id": "text-schemas"
        },
        {
          "type": "arrow",
          "id": "edge-schemas-classify-6"
        }
      ],
      "updated": 1760000000000,
      "link": null,
      "locked": false
    },
    {
      "id": "node-mock",
      "type": "rectangle",
      "x": 940,
      "y": 297.0,
      "width": 180,
      "height": 120,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "#f1f5f9",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "seed": 124247657,
      "version": 1,
      "versionNonce": 177726397,
      "isDeleted": false,
      "boundElements": [
        {
          "type": "text",
          "id": "text-mock"
        }
      ],
      "updated": 1760000000000,
      "link": null,
      "locked": false
    },
    {
      "id": "node-llm",
      "type": "rectangle",
      "x": 920,
      "y": 537.0,
      "width": 220,
      "height": 120,
      "angle": 0,
      "strokeColor": "#6d28d9",
      "backgroundColor": "#ede9fe",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "seed": 874644524,
      "version": 1,
      "versionNonce": 46892294,
      "isDeleted": false,
      "boundElements": [
        {
          "type": "text",
          "id": "text-llm"
        }
      ],
      "updated": 1760000000000,
      "link": null,
      "locked": false
    },
    {
      "id": "node-validate",
      "type": "rectangle",
      "x": 1280,
      "y": 97.0,
      "width": 180,
      "height": 120,
      "angle": 0,
      "strokeColor": "#3730a3",
      "backgroundColor": "#e0e7ff",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "seed": 361436301,
      "version": 1,
      "versionNonce": 308299114,
      "isDeleted": false,
      "boundElements": [
        {
          "type": "text",
          "id": "text-validate"
        },
        {
          "type": "arrow",
          "id": "edge-extract-validate-3"
        },
        {
          "type": "arrow",
          "id": "edge-validate-route-4"
        }
      ],
      "updated": 1760000000000,
      "link": null,
      "locked": false
    },
    {
      "id": "node-route",
      "type": "rectangle",
      "x": 1280,
      "y": 297.0,
      "width": 200,
      "height": 120,
      "angle": 0,
      "strokeColor": "#3730a3",
      "backgroundColor": "#e0e7ff",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "seed": 1519035051,
      "version": 1,
      "versionNonce": 1799676777,
      "isDeleted": false,
      "boundElements": [
        {
          "type": "text",
          "id": "text-route"
        },
        {
          "type": "arrow",
          "id": "edge-validate-route-4"
        },
        {
          "type": "arrow",
          "id": "edge-route-eval-5"
        }
      ],
      "updated": 1760000000000,
      "link": null,
      "locked": false
    },
    {
      "id": "node-eval",
      "type": "rectangle",
      "x": 1280,
      "y": 537.0,
      "width": 180,
      "height": 100,
      "angle": 0,
      "strokeColor": "#3730a3",
      "backgroundColor": "#e0e7ff",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": {
        "type": 3
      },
      "seed": 533451493,
      "version": 1,
      "versionNonce": 282126584,
      "isDeleted": false,
      "boundElements": [
        {
          "type": "text",
          "id": "text-eval"
        },
        {
          "type": "arrow",
          "id": "edge-route-eval-5"
        }
      ],
      "updated": 1760000000000,
      "link": null,
      "locked": false
    },
    {
      "id": "edge-docgen-pdftext-0",
      "type": "arrow",
      "x": 188.0,
      "y": 152.0,
      "width": 124.0,
      "height": 0.0,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [
        "grp-edge-docgen-pdftext-0"
      ],
      "frameId": null,
      "roundness": null,
      "seed": 558054660,
      "version": 1,
      "versionNonce": 114143899,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "points": [
        [
          0.0,
          0.0
        ],
        [
          124.0,
          0.0
        ]
      ],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "node-docgen",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "node-pdftext",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    },
    {
      "id": "label-edge-docgen-pdftext-0",
      "type": "text",
      "x": 234.5,
      "y": 124.0,
      "width": 31.0,
      "height": 20.0,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [
        "grp-edge-docgen-pdftext-0"
      ],
      "frameId": null,
      "roundness": null,
      "seed": 1840251964,
      "version": 1,
      "versionNonce": 1009485075,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "PDF",
      "fontSize": 16,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 13.12,
      "containerId": null,
      "originalText": "PDF",
      "lineHeight": 1.25
    },
    {
      "id": "edge-pdftext-classify-1",
      "type": "arrow",
      "x": 508.0,
      "y": 152.0,
      "width": 64.0,
      "height": 0.0,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 1427868757,
      "version": 1,
      "versionNonce": 1584950964,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "points": [
        [
          0.0,
          0.0
        ],
        [
          64.0,
          0.0
        ]
      ],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "node-pdftext",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "node-classify",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    },
    {
      "id": "edge-classify-extract-2",
      "type": "arrow",
      "x": 768.0,
      "y": 152.0,
      "width": 144.0,
      "height": 0.0,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [
        "grp-edge-classify-extract-2"
      ],
      "frameId": null,
      "roundness": null,
      "seed": 485635325,
      "version": 1,
      "versionNonce": 1187775993,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "points": [
        [
          0.0,
          0.0
        ],
        [
          144.0,
          0.0
        ]
      ],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "node-classify",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "node-extract",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    },
    {
      "id": "label-edge-classify-extract-2",
      "type": "text",
      "x": 826.0,
      "y": 124.0,
      "width": 28.0,
      "height": 20.0,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [
        "grp-edge-classify-extract-2"
      ],
      "frameId": null,
      "roundness": null,
      "seed": 1174269003,
      "version": 1,
      "versionNonce": 61086300,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "유형",
      "fontSize": 16,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 13.12,
      "containerId": null,
      "originalText": "유형",
      "lineHeight": 1.25
    },
    {
      "id": "edge-extract-validate-3",
      "type": "arrow",
      "x": 1148.0,
      "y": 152.0,
      "width": 124.0,
      "height": 0.0,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [
        "grp-edge-extract-validate-3"
      ],
      "frameId": null,
      "roundness": null,
      "seed": 940875418,
      "version": 1,
      "versionNonce": 557857711,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "points": [
        [
          0.0,
          0.0
        ],
        [
          124.0,
          0.0
        ]
      ],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "node-extract",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "node-validate",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    },
    {
      "id": "label-edge-extract-validate-3",
      "type": "text",
      "x": 1188.5,
      "y": 124.0,
      "width": 43.0,
      "height": 20.0,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [
        "grp-edge-extract-validate-3"
      ],
      "frameId": null,
      "roundness": null,
      "seed": 243975937,
      "version": 1,
      "versionNonce": 1885446000,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "JSON",
      "fontSize": 16,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 13.12,
      "containerId": null,
      "originalText": "JSON",
      "lineHeight": 1.25
    },
    {
      "id": "edge-validate-route-4",
      "type": "arrow",
      "x": 1375.0,
      "y": 225.0,
      "width": 0.0,
      "height": 64.0,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 588061820,
      "version": 1,
      "versionNonce": 1975326339,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "points": [
        [
          0.0,
          0.0
        ],
        [
          0.0,
          64.0
        ]
      ],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "node-validate",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "node-route",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    },
    {
      "id": "edge-route-eval-5",
      "type": "arrow",
      "x": 1375.0,
      "y": 425.0,
      "width": 0.0,
      "height": 104.0,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [
        "grp-edge-route-eval-5"
      ],
      "frameId": null,
      "roundness": null,
      "seed": 1502973220,
      "version": 1,
      "versionNonce": 549414727,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "points": [
        [
          0.0,
          0.0
        ],
        [
          0.0,
          104.0
        ]
      ],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "node-route",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "node-eval",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    },
    {
      "id": "label-edge-route-eval-5",
      "type": "text",
      "x": 1383.0,
      "y": 467.0,
      "width": 28.0,
      "height": 20.0,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [
        "grp-edge-route-eval-5"
      ],
      "frameId": null,
      "roundness": null,
      "seed": 317925851,
      "version": 1,
      "versionNonce": 1608307792,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "결과",
      "fontSize": 16,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 13.12,
      "containerId": null,
      "originalText": "결과",
      "lineHeight": 1.25
    },
    {
      "id": "edge-schemas-classify-6",
      "type": "arrow",
      "x": 675.0,
      "y": 289.0,
      "width": 0.0,
      "height": 64.0,
      "angle": 0,
      "strokeColor": "#334155",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "dashed",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 129242534,
      "version": 1,
      "versionNonce": 1333243325,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "points": [
        [
          0.0,
          0.0
        ],
        [
          0.0,
          -64.0
        ]
      ],
      "lastCommittedPoint": null,
      "startBinding": {
        "elementId": "node-schemas",
        "focus": 0,
        "gap": 8
      },
      "endBinding": {
        "elementId": "node-classify",
        "focus": 0,
        "gap": 8
      },
      "startArrowhead": null,
      "endArrowhead": "arrow"
    },
    {
      "id": "text-docgen",
      "type": "text",
      "x": 27.5,
      "y": 119.5,
      "width": 125.0,
      "height": 75.0,
      "angle": 0,
      "strokeColor": "#0f172a",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 1177642446,
      "version": 1,
      "versionNonce": 1934767409,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "docgen\n가상 PDF 30건\n+ 정답 JSON",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 66.4,
      "containerId": "node-docgen",
      "originalText": "docgen\n가상 PDF 30건\n+ 정답 JSON",
      "lineHeight": 1.25
    },
    {
      "id": "text-pdftext",
      "type": "text",
      "x": 351.0,
      "y": 122.0,
      "width": 118.0,
      "height": 50.0,
      "angle": 0,
      "strokeColor": "#0f172a",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 274455675,
      "version": 1,
      "versionNonce": 708636002,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "pdftext\nPDF → 텍스트",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 41.4,
      "containerId": "node-pdftext",
      "originalText": "pdftext\nPDF → 텍스트",
      "lineHeight": 1.25
    },
    {
      "id": "text-classify",
      "type": "text",
      "x": 613.5,
      "y": 119.5,
      "width": 113.0,
      "height": 75.0,
      "angle": 0,
      "strokeColor": "#0f172a",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 1075056379,
      "version": 1,
      "versionNonce": 183088149,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "classify\n유형 분류\n→ 스키마 선택",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 66.4,
      "containerId": "node-classify",
      "originalText": "classify\n유형 분류\n→ 스키마 선택",
      "lineHeight": 1.25
    },
    {
      "id": "text-extract",
      "type": "text",
      "x": 952.0,
      "y": 122.0,
      "width": 156.0,
      "height": 50.0,
      "angle": 0,
      "strokeColor": "#0f172a",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 251127429,
      "version": 1,
      "versionNonce": 1418297621,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "extract\n재시도 · 구조화 출력",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 41.4,
      "containerId": "node-extract",
      "originalText": "extract\n재시도 · 구조화 출력",
      "lineHeight": 1.25
    },
    {
      "id": "text-schemas",
      "type": "text",
      "x": 605.5,
      "y": 319.5,
      "width": 149.0,
      "height": 75.0,
      "angle": 0,
      "strokeColor": "#0f172a",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 505264648,
      "version": 1,
      "versionNonce": 899482646,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "schemas\ncontract · quote\n· invoice.json",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 66.4,
      "containerId": "node-schemas",
      "originalText": "schemas\ncontract · quote\n· invoice.json",
      "lineHeight": 1.25
    },
    {
      "id": "text-mock",
      "type": "text",
      "x": 965.0,
      "y": 319.5,
      "width": 130.0,
      "height": 75.0,
      "angle": 0,
      "strokeColor": "#0f172a",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 1746598895,
      "version": 1,
      "versionNonce": 1280447650,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "mock\n규칙·정규식\n(기본, 키 불필요)",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 66.4,
      "containerId": "node-mock",
      "originalText": "mock\n규칙·정규식\n(기본, 키 불필요)",
      "lineHeight": 1.25
    },
    {
      "id": "text-llm",
      "type": "text",
      "x": 949.5,
      "y": 559.5,
      "width": 161.0,
      "height": 75.0,
      "angle": 0,
      "strokeColor": "#0f172a",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 1681737382,
      "version": 1,
      "versionNonce": 1999830982,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "gemini · anthropic\n· openai\n(키 있을 때만)",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 66.4,
      "containerId": "node-llm",
      "originalText": "gemini · anthropic\n· openai\n(키 있을 때만)",
      "lineHeight": 1.25
    },
    {
      "id": "text-validate",
      "type": "text",
      "x": 1304.5,
      "y": 119.5,
      "width": 131.0,
      "height": 75.0,
      "angle": 0,
      "strokeColor": "#0f172a",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 534355885,
      "version": 1,
      "versionNonce": 259838448,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "validate\nJSON Schema\n+ 업무 규칙",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 66.4,
      "containerId": "node-validate",
      "originalText": "validate\nJSON Schema\n+ 업무 규칙",
      "lineHeight": 1.25
    },
    {
      "id": "text-route",
      "type": "text",
      "x": 1309.5,
      "y": 319.5,
      "width": 141.0,
      "height": 75.0,
      "angle": 0,
      "strokeColor": "#0f172a",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 1920930020,
      "version": 1,
      "versionNonce": 1751241430,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "route\n저장 / 확인 대기열\n+ 알림",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 66.4,
      "containerId": "node-route",
      "originalText": "route\n저장 / 확인 대기열\n+ 알림",
      "lineHeight": 1.25
    },
    {
      "id": "text-eval",
      "type": "text",
      "x": 1305.5,
      "y": 562.0,
      "width": 129.0,
      "height": 50.0,
      "angle": 0,
      "strokeColor": "#0f172a",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 538345700,
      "version": 1,
      "versionNonce": 1356854145,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "eval\n정답 대비 리포트",
      "fontSize": 20,
      "fontFamily": 2,
      "textAlign": "center",
      "verticalAlign": "middle",
      "baseline": 41.4,
      "containerId": "node-eval",
      "originalText": "eval\n정답 대비 리포트",
      "lineHeight": 1.25
    },
    {
      "id": "title",
      "type": "text",
      "x": 0,
      "y": 0.0,
      "width": 486.0,
      "height": 35.0,
      "angle": 0,
      "strokeColor": "#0f172a",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 159451258,
      "version": 1,
      "versionNonce": 1971650405,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "구조 — 공급자만 바꾸면 같은 검증·분기·평가",
      "fontSize": 28,
      "fontFamily": 2,
      "textAlign": "left",
      "verticalAlign": "top",
      "baseline": 22.96,
      "containerId": null,
      "originalText": "구조 — 공급자만 바꾸면 같은 검증·분기·평가",
      "lineHeight": 1.25
    },
    {
      "id": "subtitle",
      "type": "text",
      "x": 0,
      "y": 41.0,
      "width": 551.0,
      "height": 20.0,
      "angle": 0,
      "strokeColor": "#64748b",
      "backgroundColor": "transparent",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 0,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": null,
      "seed": 1919961959,
      "version": 1,
      "versionNonce": 869340623,
      "isDeleted": false,
      "boundElements": null,
      "updated": 1760000000000,
      "link": null,
      "locked": false,
      "text": "키가 없으면 모의 추출기(규칙·정규식, LLM 아님), 키가 있으면 Gemini·Claude·OpenAI",
      "fontSize": 16,
      "fontFamily": 2,
      "textAlign": "left",
      "verticalAlign": "top",
      "baseline": 13.12,
      "containerId": null,
      "originalText": "키가 없으면 모의 추출기(규칙·정규식, LLM 아님), 키가 있으면 Gemini·Claude·OpenAI",
      "lineHeight": 1.25
    }
  ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```
%%
# Text Elements
providers — 같은 출력 모양 ^zone-providers-label
PDF ^label-edge-docgen-pdftext-0
유형 ^label-edge-classify-extract-2
JSON ^label-edge-extract-validate-3
결과 ^label-edge-route-eval-5
docgen
가상 PDF 30건
+ 정답 JSON ^text-docgen
pdftext
PDF → 텍스트 ^text-pdftext
classify
유형 분류
→ 스키마 선택 ^text-classify
extract
재시도 · 구조화 출력 ^text-extract
schemas
contract · quote
· invoice.json ^text-schemas
mock
규칙·정규식
(기본, 키 불필요) ^text-mock
gemini · anthropic
· openai
(키 있을 때만) ^text-llm
validate
JSON Schema
+ 업무 규칙 ^text-validate
route
저장 / 확인 대기열
+ 알림 ^text-route
eval
정답 대비 리포트 ^text-eval
구조 — 공급자만 바꾸면 같은 검증·분기·평가 ^title
키가 없으면 모의 추출기(규칙·정규식, LLM 아님), 키가 있으면 Gemini·Claude·OpenAI ^subtitle
%%
