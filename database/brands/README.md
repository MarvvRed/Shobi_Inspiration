# Fragrantica brand image archive

Separate from the certified Shobi perfume catalog.

- Source: https://www.fragrantica.com/designers/
- Manifest: \`database/brands/brands_logos.json\`
- Images: \`database/assets/brand-logos/\`
- Collector: \`tools/build_fragrantica_brand_logos.py\`
- Workflow: GitHub Actions → **Build Fragrantica Brand Logo Archive**

The collector reads the 11 alphabetical directory pages (/designers-1/ through
/designers-11/), covering the full A–Z brand index rather than the popular
brands landing page. It stores brand name, profile and directory URLs, both image-source URLs when available, the selected source, local WebP path, dimensions, SHA-256 and download status. The collector prefers the original logo linked by the brand profile page (`o.*`) and falls back to the directory thumbnail (`t.*`) if the profile logo is missing or unusable. Re-running is incremental; existing thumbnail-only entries are revisited once for profile-logo discovery.

Some genuine Fragrantica brand marks are very wide and short (for example
80×9 px). The image validator accepts these wordmarks while still rejecting
tiny placeholder images.

## First run

GitHub-hosted runners may receive HTTP 429 from Fragrantica. Use the manual GitHub Actions workflow for controlled tests and collection. Do not launch a full crawl until the profile-logo pilot has been checked. The GitHub Actions workflow is manual-only to avoid unnecessary runs. It defaults to a safe pilot of one directory page and 30 brands; increase the limits only after confirming that original profile logos are being found.

The GitHub Actions workflow remains available as a secondary option, but a
429 from Fragrantica is an upstream rate limit, not a GitHub configuration
error. Do not repeatedly rerun it while the site is rejecting the runner.
Images are resized to at most 640×640 and stored as WebP (quality 88).
The archive records source provenance; it does not imply that reuse is licensed
or endorsed by Fragrantica or the represented brands. Check the source site's
terms and applicable rights before public redistribution.
