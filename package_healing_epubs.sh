#!/bin/bash
# Package both Healing EPUBs (bilingual and Chinese-only)
set -e

BILINGUAL_DIR="/home/user/Yohoa/Healing_Bilingual"
ZH_DIR="/home/user/Yohoa/Healing_ZH"
OUT_BILINGUAL="/home/user/Yohoa/Healing_the_Fragmented_Selves_Bilingual.epub"
OUT_ZH="/home/user/Yohoa/治愈创伤幸存者的碎裂自我-中文版.epub"

echo "=== Packaging Bilingual EPUB ==="
rm -f "$OUT_BILINGUAL"
cd "$BILINGUAL_DIR"
# mimetype must be first, uncompressed
zip -0 -X "$OUT_BILINGUAL" mimetype
# Add everything else
zip -r -9 "$OUT_BILINGUAL" META-INF ops
echo "Created: $OUT_BILINGUAL"
ls -lh "$OUT_BILINGUAL"

echo ""
echo "=== Packaging Chinese-only EPUB ==="
rm -f "$OUT_ZH"
cd "$ZH_DIR"
zip -0 -X "$OUT_ZH" mimetype
zip -r -9 "$OUT_ZH" META-INF ops
echo "Created: $OUT_ZH"
ls -lh "$OUT_ZH"

echo ""
echo "=== Integrity check ==="
python3 -c "
import zipfile, sys
for path in ['$OUT_BILINGUAL', '$OUT_ZH']:
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            assert names[0] == 'mimetype', f'mimetype not first in {path}'
            assert 'META-INF/container.xml' in names, f'Missing container.xml in {path}'
            xhtml = [n for n in names if n.endswith('.xhtml')]
            print(f'  {path}: OK ({len(names)} files, {len(xhtml)} xhtml)')
    except Exception as e:
        print(f'  ERROR in {path}: {e}', file=sys.stderr)
        sys.exit(1)
"
echo "All EPUBs passed integrity check."
