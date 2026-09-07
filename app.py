from fastapi import *
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from datetime import datetime, timedelta, timezone
import os
import re
import secrets
import json
from urllib.error import HTTPError
from urllib.request import Request as UrlRequest, urlopen
from starlette.concurrency import run_in_threadpool

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
	create_unpaid_order,
	save_payment_result,
)

def load_local_env():
	try:
		with open(".env", encoding="utf-8") as env_file:
			for line in env_file:
				key, separator, value = line.strip().partition("=")
				if separator and key and key not in os.environ:
					os.environ[key] = value
	except FileNotFoundError:
		pass


def request_tappay_payment(payload, partner_key):
	request = UrlRequest(
		"https://sandbox.tappaysdk.com/tpc/payment/pay-by-prime",
		data=json.dumps(payload).encode("utf-8"),
		headers={"Content-Type": "application/json", "x-api-key": partner_key},
		method="POST",
	)
	try:
		with urlopen(request, timeout=30) as response:
			return json.loads(response.read().decode("utf-8"))
	except HTTPError as error:
		return json.loads(error.read().decode("utf-8"))


load_local_env()
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


class AttractionSummary(BaseModel):
	id: int
	name: str
	address: str
	image: str


class TripBody(BaseModel):
	attraction: AttractionSummary
	date: str
	time: str


class ContactBody(BaseModel):
	name: str
	email: str
	phone: str


class OrderDetailBody(BaseModel):
	price: int
	trip: TripBody
	contact: ContactBody


class OrderBody(BaseModel):
	prime: str
	order: OrderDetailBody


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


@app.post("/api/orders")
async def api_create_order(body: OrderBody, request: Request, authorization: Optional[str] = Header(default=None)):
	user = authenticated_user(authorization)
	if user is None:
		return JSONResponse(status_code=403, content={"error": True, "message": "未登入系統，拒絕存取"})
	try:
		booking = get_booking_by_user_id(user["id"])
		order = body.order.model_dump()
		if not booking or order["price"] != booking["price"] or order["trip"] != {
			"attraction": booking["attraction"], "date": booking["date"], "time": booking["time"]
		}:
			raise ValueError("訂單內容與預訂資料不符")
		contact = order["contact"]
		if not contact["name"].strip() or not EMAIL_PATTERN.match(contact["email"].strip()) or not contact["phone"].strip():
			raise ValueError("聯絡資訊不完整")
		order_number = datetime.now().strftime("%Y%m%d%H%M%S%f") + secrets.token_hex(2)
		order_id = create_unpaid_order(order_number, user["id"], order["price"], order["trip"], contact)
		partner_key = os.getenv("TAPPAY_PARTNER_KEY")
		merchant_id = os.getenv("TAPPAY_MERCHANT_ID", "jessica0121_CTBC")
		if not partner_key:
			raise RuntimeError("伺服器尚未設定 TAPPAY_PARTNER_KEY")
		payment_request = {
			"prime": body.prime, "partner_key": partner_key, "merchant_id": merchant_id,
			"details": "台北一日遊行程", "amount": order["price"], "order_number": order_number,
			"cardholder": {"phone_number": contact["phone"], "name": contact["name"], "email": contact["email"]},
			"remember": False,
		}
		payment = await run_in_threadpool(request_tappay_payment, payment_request, partner_key)
		save_payment_result(order_id, payment)
		return {"data": {"number": order_number, "payment": {"status": payment.get("status"), "message": payment.get("msg", "")}}}
	except ValueError as error:
		return JSONResponse(status_code=400, content={"error": True, "message": str(error)})
	except Exception as error:
		return JSONResponse(status_code=500, content={"error": True, "message": str(error) if "TAPPAY_" in str(error) else "伺服器內部錯誤"})

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
