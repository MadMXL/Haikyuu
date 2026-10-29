# นำเข้าไลบรารี FastAPI หลักสำหรับสร้างเว็บแอปพลิเคชันและ API
from fastapi import FastAPI
# นำเข้า CORSMiddleware สำหรับจัดการและเปิดสิทธิ์การเข้าถึง API ข้ามพอร์ต (CORS)
from fastapi.middleware.cors import CORSMiddleware
# นำเข้า HTMLResponse สำหรับส่งโครงสร้างหน้าเว็บ HTML กลับไปแสดงผลที่เบราว์เซอร์
from fastapi.responses import HTMLResponse
# นำเข้า BaseModel จาก Pydantic สำหรับกำหนดโครงสร้างและตรวจสอบความถูกต้องของข้อมูล (Data Validation)
from pydantic import BaseModel

# สร้างตัวแปรหลัก (Instance) ของแอปพลิเคชัน FastAPI
app = FastAPI()

# ตั้งค่าระบบ CORS Middleware เพื่ออนุญาตให้โดเมนหรือพอร์ตอื่นสามารถดึงข้อมูลได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # เครื่องหมาย * หมายถึง อนุญาตให้ทุกเว็บไซต์หรือทุกพอร์ตเข้าถึงได้ทั้งหมด
    # อนุญาตทุก HTTP method ยกเว้น HEAD (การบ้าน: ไม่อนุญาต HEAD นอกนั้นอนุญาตทั้งหมด)
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],       # อนุญาตให้ส่งข้อมูลส่วนหัว (Headers) มาได้ทุกประเภท (เช่น Token ยืนยันตัวตน)
)

# สร้างฐานข้อมูลจำลองในหน่วยความจำ (In-memory Database) เก็บรายการสินค้าเริ่มต้น
products_db = [
    {"id": 1, "name": "iPhone 14 Pro Max", "price": 40000},
    {"id": 2, "name": "Gaming Mouse", "price": 12000}
]

# กำหนดโครงสร้างข้อมูล (Schema) ที่คาดว่าจะได้รับตอนมีคนยิงคำสั่ง POST เข้ามา
class ProductCreate(BaseModel):
    name: str  # กำหนดให้ชื่อสินค้าต้องเป็นข้อความ (String)
    price: int # กำหนดให้ราคาสินค้าต้องเป็นตัวเลขจำนวนเต็ม (Integer)

# สร้าง Route หลัก (หน้าแรก /) เมื่อมีคนเปิดเข้าเว็บไซต์ผ่านเบราว์เซอร์
@app.get("/", response_class=HTMLResponse)
def home():
    # ส่งโค้ด HTML หน้าเว็บแบบเรียบง่ายและคลีนที่สุดกลับไปแสดงผล
    return """
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>CORS Demo</title>
    </head>
    <body>
        <h2>CORS Middleware Demo</h2>
        <p>ทดสอบการดึงข้อมูล API ข้ามพอร์ตผ่าน FastAPI</p>
        
        <!-- ปุ่มกดสำหรับเรียกใช้งานฟังก์ชัน JavaScript เพื่อดึงข้อมูล API -->
        <button onclick="getData()">ดึงข้อมูลสินค้า (GET)</button>
        <!-- พื้นที่กล่องข้อความสำหรับแสดงผลลัพธ์ JSON ที่ได้จาก Backend -->
        <pre id="output">รอผลลัพธ์...</pre>

        <!-- ปุ่มกดสำหรับเรียก HEAD /foo ซึ่งจะโดน CORS บล็อก เพราะ HEAD ไม่อยู่ใน allow_methods -->
        <button onclick="callHeadFoo()">เรียก HEAD /foo</button>
        <pre id="head-output">รอผลลัพธ์...</pre>

        <script>
            // ฟังก์ชัน JavaScript สำหรับดึงข้อมูลจาก Backend แบบ Asynchronous
            async function getData() {
                try {
                    // ส่งคำขอแบบ GET ไปที่ Endpoint /api/products
                    const res = await fetch('/api/products');
                    // แปลงผลลัพธ์ที่ได้ให้อยู่ในรูปของ JSON
                    const data = await res.json();
                    // นำข้อมูลที่แปลงแล้วมาแสดงผลลงในแท็ก <pre id="output">
                    document.getElementById('output').innerText = "📦 รายการสินค้า:\\n" + JSON.stringify(data, null, 2);
                } catch (err) {
                    // หากเกิดข้อผิดพลาดหรือโดน CORS บล็อก จะแสดงข้อความแจ้งเตือนที่นี่
                    document.getElementById('output').innerText = "CORS Error: " + err;
                }
            }

            // ฟังก์ชันเรียก HEAD /foo แบบข้าม Origin เพื่อให้เบราว์เซอร์ตรวจสอบ CORS
            async function callHeadFoo() {
                // CORS ทำงานเฉพาะตอนข้าม Origin เท่านั้น จึงสลับ localhost <-> 127.0.0.1 (นับเป็นคนละ Origin)
                const host = location.hostname === 'localhost' ? '127.0.0.1' : 'localhost';
                const url = location.protocol + '//' + host + ':' + location.port + '/foo';
                try {
                    // HEAD เป็น "simple method" ปกติเบราว์เซอร์จะไม่ส่ง preflight
                    // จึงใส่ header พิเศษเพื่อบังคับให้ส่ง OPTIONS preflight ไปถามก่อนว่าอนุญาต HEAD ไหม
                    const res = await fetch(url, {
                        method: 'HEAD',
                        headers: { 'X-Homework': 'cors-head' }
                    });
                    document.getElementById('head-output').innerText = "HEAD สำเร็จ: status " + res.status;
                } catch (err) {
                    // Server ตอบ preflight ว่าไม่อนุญาต HEAD -> เบราว์เซอร์บล็อกและโยน TypeError ออกมา
                    document.getElementById('head-output').innerText =
                        "CORS Error: " + err + "\\n(เปิด DevTools > Console เพื่อดูข้อความ CORS แบบเต็ม)";
                }
            }
        </script>
    </body>
    </html>
    """

# สร้าง API สำหรับรองรับคำสั่ง GET (ดึงข้อมูลสินค้าทั้งหมดส่งกลับไป)
@app.get("/api/products")
def get_products():
    return products_db # ส่งข้อมูลรายการสินค้าทั้งหมดในฐานข้อมูลจำลองกลับไป

# สร้าง API สำหรับรองรับคำสั่ง POST (รับข้อมูลสินค้าใหม่เข้ามาเพิ่มในระบบ)
@app.post("/api/products")
def add_product(product: ProductCreate):
    # สร้างไอดีใหม่โดยนับจำนวนสินค้าเดิมบวก 1 และนำชื่อกับราคาจากที่ผู้ใช้ส่งมาสร้างเป็นสินค้าชิ้นใหม่
    new_item = {
        "id": len(products_db) + 1,
        "name": product.name,
        "price": product.price
    }
    # บันทึกสินค้าใหม่เข้าไปในฐานข้อมูลจำลอง (products_db)
    products_db.append(new_item)
    # ส่งสถานะความสำเร็จและข้อมูลสินค้าที่เพิ่งเพิ่มใหม่กลับไปหาผู้ส่ง
    return {"status": "success", "added": new_item, "total_items": len(products_db)}

# สร้าง API สำหรับรองรับคำสั่ง HEAD (การบ้าน: endpoint นี้จะถูก CORS บล็อกเมื่อเรียกข้าม Origin)
@app.head("/foo")
def head_foo():
    return {"message": "foo"} # HEAD จะส่งกลับเฉพาะ headers ไม่มี body
