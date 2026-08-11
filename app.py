from fastapi import *
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from database.queries import (
	get_attraction_by_id,
	get_attractions,
	get_categories,
	get_mrts,
)

app=FastAPI()

# Front-end assets are kept separate from the HTML file.
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/api/attractions")
async def api_attractions(
	page: int = Query(..., ge=0),
	category: Optional[str] = None,
	keyword: Optional[str] = None,
):
	try:
		return get_attractions(page=page, keyword=keyword, category=category)
	except Exception:
		return JSONResponse(
			status_code=500,
			content={"error": True, "message": "伺服器內部錯誤"},
		)

@app.get("/api/attraction/{attractionId}")
async def api_attraction(attractionId: int):
	try:
		attraction = get_attraction_by_id(attractionId)
		if attraction is None:
			return JSONResponse(
				status_code=400,
				content={"error": True, "message": "景點編號不正確"},
			)
		return {"data": attraction}
	except Exception:
		return JSONResponse(
			status_code=500,
			content={"error": True, "message": "伺服器內部錯誤"},
		)

@app.get("/api/mrts")
async def api_mrts():
	try:
		return {"data": get_mrts()}
	except Exception:
		return JSONResponse(
			status_code=500,
			content={"error": True, "message": "伺服器內部錯誤"},
		)

@app.get("/api/categories")
async def api_categories():
	try:
		return {"data": get_categories()}
	except Exception:
		return JSONResponse(
			status_code=500,
			content={"error": True, "message": "伺服器內部錯誤"},
		)

# Static Pages (Never Modify Code in this Block)
@app.get("/", include_in_schema=False)
async def index(request: Request):
	return FileResponse("./static/index.html", media_type="text/html")
@app.get("/attraction/{id}", include_in_schema=False)
async def attraction(request: Request, id: int):
	return FileResponse("./static/attraction.html", media_type="text/html")
@app.get("/booking", include_in_schema=False)
async def booking(request: Request):
	return FileResponse("./static/booking.html", media_type="text/html")
@app.get("/thankyou", include_in_schema=False)
async def thankyou(request: Request):
	return FileResponse("./static/thankyou.html", media_type="text/html")
