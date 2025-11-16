# iRunner to ICPC Converter

This script converts contest data exported from iRunner (an ejudge-compatible system) into the ICPC Contest Package Format, which is compatible with the ICPC Resolver.

## Description

The script takes an XML export file from iRunner and generates a directory containing the necessary files for an ICPC contest package, including `event-feed.ndjson` and other metadata.

It was created specifically for the Belarusian Regional Contest 2025.

## Usage

Run the script with Python 3:

```bash
python irunner2icpc_converter.py <input_xml_file> <output_directory>
```

- `<input_xml_file>`: Path to the iRunner export XML file (e.g., `brc25m-ejudge.xml`).
- `<output_directory>`: Path to the directory where the ICPC package will be created (e.g., `icpc_package`).

## Prerequisites

- Python 3.x
- Standard libraries: `json`, `xml.etree.ElementTree`, `os`, `datetime`, `argparse`

## Links

- [iRunner](https://acm.bsu.by/)
- [ICPC Contest Package Format](https://ccs-specs.icpc.io/2023-06/contest_package)
- [ICPC Resolver](https://tools.icpc.global/resolver/)