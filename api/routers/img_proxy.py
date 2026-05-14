import os
from fastapi import APIRouter, Query, Response
import httpx

router = APIRouter()

GMAPS_KEY = os.environ.get("GOOGLE_MAPS_KEY", "")

ZILLOW_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.zillow.com/",
    "Accept": "image/webp,image/avif,image/*,*/*",
}


def _street_view_url(address: str) -> str:
    loc = address.strip().replace(" ", "+") + "+Austin+TX"
    return (
        f"https://maps.googleapis.com/maps/api/streetview"
        f"?size=640x400&location={loc}&key={GMAPS_KEY}"
    )


@router.get("/img-proxy")
async def img_proxy(url: str = Query(default=""), address: str = Query(default="")):
    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
        # Try original URL first if provided and not a known-dead format
        if url and url.startswith("http"):
            is_old_kaggle = "zillowstatic.com/fp/" in url and "_p_f.jpg" in url
            if not is_old_kaggle:
                try:
                    r = await client.get(url, headers=ZILLOW_HEADERS)
                    if r.status_code == 200:
                        ct = r.headers.get("content-type", "image/jpeg")
                        return Response(content=r.content, media_type=ct,
                                        headers={"Cache-Control": "public, max-age=86400"})
                except Exception:
                    pass

        # Fallback: Google Street View
        if address and GMAPS_KEY:
            try:
                sv_url = _street_view_url(address)
                r = await client.get(sv_url)
                if r.status_code == 200:
                    ct = r.headers.get("content-type", "image/jpeg")
                    return Response(content=r.content, media_type=ct,
                                    headers={"Cache-Control": "public, max-age=3600"})
            except Exception:
                pass

    return Response(status_code=404)
