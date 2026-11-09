# Fragrantica brand image archive

Separate from the certified Shobi perfume catalog.

- Source: https://www.fragrantica.com/designers/
- Manifest: \`database/brands/brands_logos.json\`
- Images: \`database/assets/brand-logos/\`
- Collector: \`tools/build_fragrantica_brand_logos.py\`
- Workflow: GitHub Actions → **Build Fragrantica Brand Logo Archive**

The collector reads the 11 alphabetical directory pages (/designers-1/ through
/designers-11/), covering the full A–Z brand index rather than the popular
brands landing page. It stores brand name, source page and image URLs, local
WebP path, dimensions, SHA-256 and download status. Re-running is incremental
and skips images already downloaded; the Windows runner retries prior failures.

Some genuine Fragrantica brand marks are very wide and short (for example
80×9 px). The image validator accepts these wordmarks while still rejecting
tiny placeholder images.

## First run

GitHub-hosted runners may receive HTTP 429 from Fragrantica. Prefer the local
Windows runner at tools/run_brand_logo_pilot_windows.bat: run it from a
local clone of this repository on main. It creates an isolated Python
environment, installs dependencies, runs a conservative pilot (defaults:
1 directory page, 30 brands, 4-second delay), then commits and pushes only the
brand manifest and logo assets. You can change the page and brand limits when
prompted.

The GitHub Actions workflow remains available as a secondary option, but a
429 from Fragrantica is an upstream rate limit, not a GitHub configuration
error. Do not repeatedly rerun it while the site is rejecting the runner.
Images are resized to at most 640×640 and stored as WebP (quality 88).
The archive records source provenance; it does not imply that reuse is licensed
or endorsed by Fragrantica or the represented brands. Check the source site's
terms and applicable rights before public redistribution.
