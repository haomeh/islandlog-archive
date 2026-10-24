# Attribution

This file lists the open data that archive reuses and the attribution that its license requires (PRD D7, R-08).

## Administrative boundaries (jurisdictions and `geo/`)

| Item | Value |
|---|---|
| Data | 直轄市、縣市界線(TWD97經緯度) (county and city boundaries, TWD97 longitude and latitude) |
| Provider | 內政部 (Ministry of the Interior), via 政府資料開放平臺 |
| Dataset page | https://data.gov.tw/dataset/7442 |
| File | https://www.tgos.tw/tgos/VirtualDir/Product/1cd4f4c9-6b01-4cf9-bf6c-23a73aa17d24/直轄市、縣(市)界線1140318.zip (SHP, version 1140318) |
| License | 政府資料開放授權條款－第1版 (Open Government Data License, Taiwan, version 1.0). data.gov.tw lists license code `1` for this dataset. |
| Downloaded | 2026-10-24 |
| SHA-256 of the zip | `9ff4d337e03a711d7e17caaf4d0c46a0fe2c6bd3660b321a2e35123030d8491c` |
| Changes | Geometry simplified (tolerance 0.002 degrees), rounded to 0.0001 degrees and converted to TopoJSON (`geo/counties.topo.json`). Each county got the ID `jur-<official_code>`. |

Attribution line:
> 資料來源：內政部，直轄市、縣市界線(TWD97經緯度)，依政府資料開放授權條款－第1版提供。本專案已簡化幾何並轉換為 TopoJSON。

## Source files

Each file in `sources/` that has `license: ogdl-tw-1.0` carries its own `attribution` field.
