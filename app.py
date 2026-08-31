from fastapi import *
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from datetime import datetime, timedelta, timezone
import os
import re

import jwt
from jwt import InvalidTokenError
from mysql.connector import IntegrityError
from pydantic import BaseModel
from database.queries import (
	delete_booking_by_user_id,
	create_user,
	get_booking_by_user_id,
	get_attraction_by_id,
	get_attractions,
	get_categories,
	get_mrts,
	get_user_by_email,
	verify_password,
	upsert_booking,
)

app=FastAPI()

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "change-this-secret-in-production")
JWT_ALGORITHM = "HS256"
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class SignUpBody(BaseModel):
	name: str
	email: str
	password: str


class SignInBody(BaseModel):
	email: str
	password: str


class BookingBody(BaseModel):
	attractionId: int
	date: str
	time: str
	price: int


def authenticated_user(authorization):
	if not authorization or not authorization.startswith("Bearer "):
		return None
	try:
		return jwt.decode(
			authorization.removeprefix("Bearer ").strip(),
			JWT_SECRET,
			algorithms=[JWT_ALGORITHM],
		)
	except (InvalidTokenError, KeyError, TypeError):
		return None

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


@app.post("/api/user")
async def api_user_signup(body: SignUpBody):
	name = body.name.strip()
	email = body.email.strip().lower()
	if not name or not EMAIL_PATTERN.match(email) or len(body.password) < 4:
		return JSONResponse(
			status_code=400,
			content={"error": True, "message": "姓名、電子信箱或密碼格式不正確"},
		)
	try:
		create_user(name, email, body.password)
		return {"ok": True}
	except IntegrityError:
		return JSONResponse(
			status_code=400,
			content={"error": True, "message": "此電子信箱已經註冊"},
		)
	except Exception:
		return JSONResponse(
			status_code=500,
			content={"error": True, "message": "伺服器內部錯誤"},
		)


@app.put("/api/user/auth")
async def api_user_signin(body: SignInBody):
	email = body.email.strip().lower()
	try:
		user = get_user_by_email(email)
		if user is None or not verify_password(body.password, user["password"]):
			return JSONResponse(
				status_code=400,
				content={"error": True, "message": "電子信箱或密碼錯誤"},
			)
		payload = {
			"id": user["id"],
			"name": user["name"],
			"email": user["email"],
			"exp": datetime.now(timezone.utc) + timedelta(days=7),
		}
		token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
		return {"token": token}
	except Exception:
		return JSONResponse(
			status_code=500,
			content={"error": True, "message": "伺服器內部錯誤"},
		)


@app.get("/api/user/auth")
async def api_user_auth(authorization: Optional[str] = Header(default=None)):
	if not authorization or not authorization.startswith("Bearer "):
		return {"data": None}
	token = authorization.removeprefix("Bearer ").strip()
	try:
		payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
		return {
			"data": {
				"id": payload["id"],
				"name": payload["name"],
				"email": payload["email"],
			}
		}
	except (InvalidTokenError, KeyError, TypeError):
		return {"data": None}


@app.get("/api/booking")
async def api_get_booking(authorization: Optional[str] = Header(default=None)):
	user = authenticated_user(authorization)
	if user is None:
		return JSONResponse(status_code=403, content={"error": True, "message": "未登入系統，拒絕存取"})
	try:
		return {"data": get_booking_by_user_id(user["id"])}
	except Exception:
		return JSONResponse(status_code=500, content={"error": True, "message": "伺服器內部錯誤"})


@app.post("/api/booking")
async def api_create_booking(body: BookingBody, authorization: Optional[str] = Header(default=None)):
	user = authenticated_user(authorization)
	if user is None:
		return JSONResponse(status_code=403, content={"error": True, "message": "未登入系統，拒絕存取"})
	try:
		booking_date = datetime.strptime(body.date, "%Y-%m-%d").date()
		if body.attractionId < 1 or body.time not in ("morning", "afternoon") or body.price not in (2000, 2500):
			raise ValueError
		if get_attraction_by_id(body.attractionId) is None:
			raise ValueError
		upsert_booking(user["id"], body.attractionId, booking_date, body.time, body.price)
		return {"ok": True}
	except ValueError:
		return JSONResponse(status_code=400, content={"error": True, "message": "建立預訂失敗，輸入不正確或其他原因"})
	except Exception:
		return JSONResponse(status_code=500, content={"error": True, "message": "伺服器內部錯誤"})


@app.delete("/api/booking")
async def api_delete_booking(authorization: Optional[str] = Header(default=None)):
	user = authenticated_user(authorization)
	if user is None:
		return JSONResponse(status_code=403, content={"error": True, "message": "未登入系統，拒絕存取"})
	try:
		delete_booking_by_user_id(user["id"])
		return {"ok": True}
	except Exception:
		return JSONResponse(status_code=500, content={"error": True, "message": "伺服器內部錯誤"})

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
