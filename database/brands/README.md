# Fragrantica brand image archive

Separate from the certified Shobi perfume catalog.

- Source: https://www.fragrantica.com/designers/
- Manifest: \`database/brands/brands_logos.json\`
- Images: \`database/assets/brand-logos/\`
- Collector: \`tools/build_fragrantica_brand_logos.py\`
- Workflow: GitHub Actions → **Build Fragrantica Brand Logo Archive**

The collector discovers directory pagination instead of assuming a fixed page
count. It stores brand name, source page and image URLs, local WebP path,
dimensions, SHA-256 and download status. Failed downloads remain explicitly
failed. Re-running is incremental and skips images already downloaded.

## First run

Open **Actions → Build Fragrantica Brand Logo Archive → Run workflow**.
For a pilot, use \`max_pages=1\` and \`limit=30\`. Inspect the resulting images
and manifest before the full run. Set \`retry_failed=true\` to retry failed rows.

Images are resized to at most 640×640 and stored as WebP (quality 88).
The archive records source provenance; it does not imply that reuse is licensed
or endorsed by Fragrantica or the represented brands. Check the source site's
terms and applicable rights before public redistribution.
