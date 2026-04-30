# api/gallery_banner.py
import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from models.gallery_banner_models import SchoolBanner, SchoolGallery
from response.result import Result

gallery_banner_router = APIRouter(tags=["GALLERY & BANNER"])

# ── Upload config ──────────────────────────────────────────────────────────────
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/var/www/html/images")
BASE_URL   = os.getenv("BASE_URL",   "http://69.62.77.182/images")

try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except Exception:
    pass


# ── Image upload helper ────────────────────────────────────────────────────────

async def _save_image(file: UploadFile) -> str:
    ext      = file.filename.split(".")[-1].lower() if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    path     = os.path.join(UPLOAD_DIR, filename)
    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)
    os.chmod(path, 0o644)
    return f"{BASE_URL}/{filename}"


def _delete_file(url: str):
    """Remove the physical file from disk if it lives in UPLOAD_DIR."""
    if url and url.startswith(BASE_URL):
        filename = url[len(BASE_URL):].lstrip("/")
        path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(path):
            os.remove(path)


# ═══════════════════════════════════════════════════════════════════════════════
#  GALLERY
# ═══════════════════════════════════════════════════════════════════════════════

# ── POST /gallery/ — upload one or more images ────────────────────────────────

@gallery_banner_router.post("/gallery/")
async def create_gallery(
    school_id: int               = Form(...),
    status:    int               = Form(1),       # 1=active, 0=inactive
    files:     List[UploadFile]  = File(...),
    db:        AsyncSession      = Depends(get_db),
):
    """
    Upload one or more gallery images.
    Returns the saved records with their image URLs.
    """
    if not files:
        return Result(code=400, message="No files provided.").http_response()

    saved = []
    for file in files:
        if not file.filename:
            continue

        url = await _save_image(file)

        row = SchoolGallery(school_id=school_id, bannerlink=url, status=status)
        db.add(row)
        await db.flush()        # get row.id before commit
        saved.append({"id": row.id, "image_url": url, "status": status})

    await db.commit()

    return Result(
        code=200,
        message=f"{len(saved)} image(s) uploaded.",
        extra={"gallery": saved},
    ).http_response()


# ── GET /gallery/ — list all ──────────────────────────────────────────────────

@gallery_banner_router.get("/gallery/")
async def get_gallery(
    school_id:  Optional[int] = None,
    status:     Optional[int] = None,    # 1 or 0
    page:       int           = 1,
    page_size:  int           = 20,
    db:         AsyncSession  = Depends(get_db),
):
    stmt = select(SchoolGallery)
    if school_id is not None:
        stmt = stmt.where(SchoolGallery.school_id == school_id)
    if status is not None:
        stmt = stmt.where(SchoolGallery.status == status)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        stmt.order_by(SchoolGallery.id.desc()).offset(offset).limit(page_size)
    )
    items = [
        {
            "id":         g.id,
            "school_id":  g.school_id,
            "image_url":  g.bannerlink,
            "status":     g.status,
            "created_at": g.created_at.strftime("%Y-%m-%d %H:%M:%S") if g.created_at else None,
        }
        for g in result.scalars().all()
    ]

    return Result(
        code=200,
        message="Gallery fetched.",
        extra={"total": total, "page": page, "page_size": page_size, "gallery": items},
    ).http_response()


# ── GET /gallery/{id}/ — single item ─────────────────────────────────────────

@gallery_banner_router.get("/gallery/{gallery_id}/")
async def get_gallery_item(
    gallery_id: int,
    db:         AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SchoolGallery).where(SchoolGallery.id == gallery_id))
    g = result.scalar_one_or_none()
    if not g:
        return Result(code=404, message="Gallery item not found.").http_response()

    return Result(
        code=200,
        message="Gallery item fetched.",
        extra={
            "id":         g.id,
            "school_id":  g.school_id,
            "image_url":  g.bannerlink,
            "status":     g.status,
            "created_at": g.created_at.strftime("%Y-%m-%d %H:%M:%S") if g.created_at else None,
        },
    ).http_response()


# ── PUT /gallery/{id}/ — update image or status ───────────────────────────────

@gallery_banner_router.put("/gallery/{gallery_id}/")
async def update_gallery(
    gallery_id: int,
    status:     Optional[int]         = Form(None),
    file:       Optional[UploadFile]  = File(None),
    db:         AsyncSession          = Depends(get_db),
):
    """
    Update a gallery item.
    - Pass `file` to replace the image.
    - Pass `status` (1/0) to change active state.
    Both are optional — send only what you want to update.
    """
    result = await db.execute(select(SchoolGallery).where(SchoolGallery.id == gallery_id))
    g = result.scalar_one_or_none()
    if not g:
        return Result(code=404, message="Gallery item not found.").http_response()

    if file and file.filename:
        _delete_file(g.bannerlink)          # remove old file from disk
        g.bannerlink = await _save_image(file)

    if status is not None:
        g.status = status

    await db.commit()

    return Result(
        code=200,
        message="Gallery item updated.",
        extra={"id": g.id, "image_url": g.bannerlink, "status": g.status},
    ).http_response()


# ── DELETE /gallery/{id}/ ─────────────────────────────────────────────────────

@gallery_banner_router.delete("/gallery/{gallery_id}/")
async def delete_gallery(
    gallery_id: int,
    db:         AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SchoolGallery).where(SchoolGallery.id == gallery_id))
    g = result.scalar_one_or_none()
    if not g:
        return Result(code=404, message="Gallery item not found.").http_response()

    _delete_file(g.bannerlink)     # remove physical file
    await db.delete(g)
    await db.commit()

    return Result(code=200, message="Gallery item deleted.").http_response()


# ═══════════════════════════════════════════════════════════════════════════════
#  BANNER
# ═══════════════════════════════════════════════════════════════════════════════

# ── POST /banner/ — upload one or more banners ────────────────────────────────

@gallery_banner_router.post("/banner/")
async def create_banner(
    school_id: int               = Form(...),
    status:    int               = Form(1),
    files:     List[UploadFile]  = File(...),
    db:        AsyncSession      = Depends(get_db),
):
    """
    Upload one or more banner images.
    Returns the saved records with their image URLs.
    """
    if not files:
        return Result(code=400, message="No files provided.").http_response()

    saved = []
    for file in files:
        if not file.filename:
            continue

        url = await _save_image(file)

        row = SchoolBanner(school_id=school_id, bannerlink=url, status=status)
        db.add(row)
        await db.flush()
        saved.append({"id": row.id, "image_url": url, "status": status})

    await db.commit()

    return Result(
        code=200,
        message=f"{len(saved)} banner(s) uploaded.",
        extra={"banners": saved},
    ).http_response()


# ── GET /banner/ — list all ───────────────────────────────────────────────────

@gallery_banner_router.get("/banner/")
async def get_banners(
    school_id:  Optional[int] = None,
    status:     Optional[int] = None,
    page:       int           = 1,
    page_size:  int           = 20,
    db:         AsyncSession  = Depends(get_db),
):
    stmt = select(SchoolBanner)
    if school_id is not None:
        stmt = stmt.where(SchoolBanner.school_id == school_id)
    if status is not None:
        stmt = stmt.where(SchoolBanner.status == status)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        stmt.order_by(SchoolBanner.id.desc()).offset(offset).limit(page_size)
    )
    items = [
        {
            "id":         b.id,
            "school_id":  b.school_id,
            "image_url":  b.bannerlink,
            "status":     b.status,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else None,
        }
        for b in result.scalars().all()
    ]

    return Result(
        code=200,
        message="Banners fetched.",
        extra={"total": total, "page": page, "page_size": page_size, "banners": items},
    ).http_response()


# ── GET /banner/{id}/ — single item ──────────────────────────────────────────

@gallery_banner_router.get("/banner/{banner_id}/")
async def get_banner(
    banner_id: int,
    db:        AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SchoolBanner).where(SchoolBanner.id == banner_id))
    b = result.scalar_one_or_none()
    if not b:
        return Result(code=404, message="Banner not found.").http_response()

    return Result(
        code=200,
        message="Banner fetched.",
        extra={
            "id":         b.id,
            "school_id":  b.school_id,
            "image_url":  b.bannerlink,
            "status":     b.status,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else None,
        },
    ).http_response()


# ── PUT /banner/{id}/ — update image or status ────────────────────────────────

@gallery_banner_router.put("/banner/{banner_id}/")
async def update_banner(
    banner_id: int,
    status:    Optional[int]        = Form(None),
    file:      Optional[UploadFile] = File(None),
    db:        AsyncSession         = Depends(get_db),
):
    """
    Update a banner.
    - Pass `file` to replace the image.
    - Pass `status` (1/0) to activate/deactivate.
    """
    result = await db.execute(select(SchoolBanner).where(SchoolBanner.id == banner_id))
    b = result.scalar_one_or_none()
    if not b:
        return Result(code=404, message="Banner not found.").http_response()

    if file and file.filename:
        _delete_file(b.bannerlink)
        b.bannerlink = await _save_image(file)

    if status is not None:
        b.status = status

    await db.commit()

    return Result(
        code=200,
        message="Banner updated.",
        extra={"id": b.id, "image_url": b.bannerlink, "status": b.status},
    ).http_response()


# ── DELETE /banner/{id}/ ──────────────────────────────────────────────────────

@gallery_banner_router.delete("/banner/{banner_id}/")
async def delete_banner(
    banner_id: int,
    db:        AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SchoolBanner).where(SchoolBanner.id == banner_id))
    b = result.scalar_one_or_none()
    if not b:
        return Result(code=404, message="Banner not found.").http_response()

    _delete_file(b.bannerlink)
    await db.delete(b)
    await db.commit()

    return Result(code=200, message="Banner deleted.").http_response()


# ── POST /upload/ (Upload image, return URL only — no DB save) ────────────────

@gallery_banner_router.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    """Upload a single image and return its public URL."""
    if not file.filename:
        return Result(code=400, message="No file provided.").http_response()

    url = await _save_image(file)
    return Result(code=200, message="Image uploaded.", extra={"url": url}).http_response()
