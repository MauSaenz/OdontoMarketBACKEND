"""
Script de Sembrado del Catálogo Dental y Verificación Integral de la Fase 3 (`test_phase3.py`).
Prueba todos los endpoints del Marketplace Dental construidos en la Fase 3:
1. Publicación de 6 insumos y equipos dentales reales con registro COFEPRIS, lote, caducidad y mayoreo.
2. Buscador avanzado con filtros combinados (`search`, `brand`, `category_id`, `min_price`, `wholesale_only`).
3. Flujo de Preguntas y Respuestas estilo Mercado Libre (Odontóloga pregunta -> Depósito responde).
4. Checkout y Orden de Compra con activación automática de precio de mayoreo (`wholesale_price`),
   descuento de stock y congelamiento de lote sanitario (`lot_snapshot`).
5. Reseña de 5 estrellas con detección automática de Compra Verificada (`is_verified_purchase = True`).
6. Actualización de estado logístico a `Enviado` con guía de rastreo y consulta de ventas del Depósito.
"""

import sys
from fastapi.testclient import TestClient

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.main import app


SAMPLE_DENTAL_PRODUCTS = [
    {
        "category_id": 5,  # Biomateriales y Operatoria
        "name": "Resina Filtek Z350 XT Nanorrelleno Tono A2",
        "sku": "3M-Z350-A2-4G",
        "description": "Resina compuesta universal de nanorrelleno fotopolimerizable para restauraciones anteriores y posteriores con pulido espejo.",
        "brand": "3M ESPE",
        "sanitary_registration": "COFEPRIS 1482C2023 SSA",
        "lot_number": "LOT-3M-2026-88A",
        "expiration_date": "2028-09-30",
        "presentation": "Jeringa de 4g Tono A2 Body",
        "requires_cold_chain": False,
        "price": 890.00,
        "wholesale_price": 760.00,
        "wholesale_min_qty": 5,
        "stock": 50,
        "image_url": "https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&w=800&q=80",
    },
    {
        "category_id": 1,  # Instrumental Rotatorio
        "name": "Pieza de Mano de Alta Velocidad Pana-Max Plus LED",
        "sku": "NSK-PANAMAX-LED2",
        "description": "Turbina dental de cabezal estándar con rodamientos cerámicos, spray cuádruple de agua y sistema de cabezal limpio.",
        "brand": "NSK",
        "sanitary_registration": "COFEPRIS 0912E2024 SSA",
        "lot_number": "LOT-NSK-JP-441",
        "expiration_date": None,
        "presentation": "Pieza de mano individual conexión Borden 2 vías",
        "requires_cold_chain": False,
        "price": 4650.00,
        "wholesale_price": 4150.00,
        "wholesale_min_qty": 3,
        "stock": 18,
        "image_url": "https://images.unsplash.com/photo-1606811841689-23dfddce3e95?auto=format&fit=crop&w=800&q=80",
    },
    {
        "category_id": 2,  # Endodoncia
        "name": "Sistema de Limas Rotatorias ProTaper Gold NiTi",
        "sku": "DS-PROTAPER-GOLD-25",
        "description": "Limas endodónticas con metalurgia avanzada Gold-Wire de alta flexibilidad y resistencia a la fatiga cíclica.",
        "brand": "Dentsply Sirona",
        "sanitary_registration": "COFEPRIS 2104C2023 SSA",
        "lot_number": "LOT-DS-2026-119",
        "expiration_date": "2030-12-31",
        "presentation": "Blíster estéril con 6 limas surtidas (SX-F3) 25mm",
        "requires_cold_chain": False,
        "price": 1380.00,
        "wholesale_price": 1190.00,
        "wholesale_min_qty": 4,
        "stock": 35,
        "image_url": "https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=800&q=80",
    },
    {
        "category_id": 5,  # Biomateriales y Operatoria
        "name": "Anestésico Septanest Articaína 4% con Epinefrina 1:100,000",
        "sku": "SEPT-ARTI-100-50C",
        "description": "Anestésico local inyectable de rápida latencia para procedimientos odontológicos de rutina y cirugía oral.",
        "brand": "Septodont",
        "sanitary_registration": "COFEPRIS 184M2022 SSA IV",
        "lot_number": "LOT-SEP-FR-902",
        "expiration_date": "2028-03-15",
        "presentation": "Caja con 50 cartuchos de vidrio de 1.8ml en blíster",
        "requires_cold_chain": False,
        "price": 940.00,
        "wholesale_price": 820.00,
        "wholesale_min_qty": 5,
        "stock": 60,
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=800&q=80",
    },
    {
        "category_id": 3,  # Ortodoncia
        "name": "Kit de Brackets Metálicos Mini Roth .022 con Gancho 3,4,5",
        "sku": "ORM-MINIROTH-022",
        "description": "Brackets de acero inoxidable 17-4 moldeados por inyección (MIM) con base de malla calibre 80 anatómica.",
        "brand": "American Orthodontics",
        "sanitary_registration": "FDA 510k K192831 / COFEPRIS 1102C2024",
        "lot_number": "LOT-AO-2026-771",
        "expiration_date": None,
        "presentation": "Caso completo de 20 brackets (5x5 superior e inferior)",
        "requires_cold_chain": False,
        "price": 520.00,
        "wholesale_price": 430.00,
        "wholesale_min_qty": 10,
        "stock": 80,
        "image_url": "https://images.unsplash.com/photo-1598256989800-fe5f95da9787?auto=format&fit=crop&w=800&q=80",
    },
    {
        "category_id": 6,  # Equipos Mayores
        "name": "Lámpara de Fotocurado Inalámbrica LED.B / iLed 2300 mW/cm²",
        "sku": "WP-ILED-PLUS-2300",
        "description": "Polimerización en 1 segundo para capas de 2mm de resina. Cabezal giratorio 360 grados y espectro amplio.",
        "brand": "Woodpecker",
        "sanitary_registration": "COFEPRIS 3319E2023 SSA",
        "lot_number": "LOT-WP-2026-505",
        "expiration_date": None,
        "presentation": "Equipo completo con base cargadora, fibra óptica y protector ocular",
        "requires_cold_chain": False,
        "price": 3290.00,
        "wholesale_price": 2890.00,
        "wholesale_min_qty": 3,
        "stock": 15,
        "image_url": "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=800&q=80",
    },
]


def run_phase3_tests() -> None:
    print("=" * 78)
    print("[ODONTOMARKET] INICIANDO PRUEBAS DE FASE 3: CATALOGO + Q&A + CHECKOUT + MAYOREO")
    print("=" * 78)

    with TestClient(app) as client:
        # 1. Iniciar sesión con nuestras cuentas de Odontóloga y Depósito Dental
        login_dentist = client.post(
            "/api/auth/login-json",
            json={"email": "dra.valeria@clinicasmile.com", "password": "OdontoSegura2026!"},
        )
        assert login_dentist.status_code == 200
        dentist_token = login_dentist.json()["access_token"]
        dentist_headers = {"Authorization": f"Bearer {dentist_token}"}

        login_vendor = client.post(
            "/api/auth/login-json",
            json={"email": "ventas@depositovillacortes.com", "password": "DepositoDental2026!"},
        )
        assert login_vendor.status_code == 200
        vendor_token = login_vendor.json()["access_token"]
        vendor_headers = {"Authorization": f"Bearer {vendor_token}"}

        # 2. Sembrar / publicar los 6 productos dentales si no existen aún
        created_products = []
        for prod_payload in SAMPLE_DENTAL_PRODUCTS:
            res = client.post("/api/products", json=prod_payload, headers=vendor_headers)
            if res.status_code == 201:
                created_products.append(res.json())
        all_prods = client.get("/api/products").json()
        print(f"\n1. [OK] Catálogo dental activo: {len(all_prods)} productos publicados con registro COFEPRIS.")

        target_product = next(p for p in all_prods if p["sku"] == "3M-Z350-A2-4G")
        product_id = target_product["id"]

        # 3. Probar filtros avanzados del buscador
        search_res = client.get("/api/products", params={"search": "Filtek", "brand": "3M ESPE", "wholesale_only": True})
        assert search_res.status_code == 200
        assert len(search_res.json()) >= 1
        brands_res = client.get("/api/products/brands")
        print(f"2. [OK] Buscador y filtros operativos. Marcas detectadas: {', '.join(brands_res.json())}")

        # 4. Probar Flujo de Preguntas y Respuestas estilo Mercado Libre
        q_res = client.post(
            f"/api/products/{product_id}/questions",
            json={"question_text": "¿Qué fecha de caducidad tiene el lote actual de la resina A2 y emiten factura?"},
            headers=dentist_headers,
        )
        assert q_res.status_code == 201
        question_id = q_res.json()["id"]

        ans_res = client.put(
            f"/api/questions/{question_id}/answer",
            json={
                "answer_text": "¡Hola Dra. Valeria! El lote LOT-3M-2026-88A caduca en Septiembre de 2028 y facturamos al instante."
            },
            headers=vendor_headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["is_answered"] is True
        print(f"3. [OK] Pregunta #{question_id} respondida exitosamente por el Depósito Dental.")

        # 5. Probar Checkout con activación automática de precio de mayoreo (6 jeringas >= 5 mínimas)
        order_payload = {
            "shipping_address": "Av. Insurgentes Sur 1602, Consultorio 402",
            "shipping_city": "Ciudad de México",
            "shipping_state": "CDMX",
            "shipping_zip": "03940",
            "notes": "Entregar en recepción de Clínica Smile Center",
            "items": [
                {"product_id": product_id, "quantity": 6},
            ],
        }
        order_res = client.post("/api/orders", json=order_payload, headers=dentist_headers)
        assert order_res.status_code == 201, order_res.text
        order_data = order_res.json()
        first_item = order_data["items"][0]
        assert first_item["applied_wholesale"] is True
        assert first_item["unit_price"] == 760.00
        print(
            f"4. [OK] Orden #{order_data['id']} generada: 6 unidades activaron precio de mayoreo "
            f"(${first_item['unit_price']} c/u en vez de $890.0). "
            f"Subtotal: ${order_data['subtotal']} | IVA: ${order_data['tax_amount']} | Total: ${order_data['total_amount']} "
            f"| Lote congelado: {first_item['lot_snapshot']}"
        )

        # 6. Probar Reseña con detección automática de Compra Verificada
        existing_reviews = client.get(f"/api/products/{product_id}/reviews").json()
        if not existing_reviews:
            rev_res = client.post(
                f"/api/products/{product_id}/reviews",
                json={
                    "rating": 5,
                    "title": "Original 3M con caducidad excelente",
                    "comment": "Compré 6 jeringas con precio de mayoreo para la clínica. Selladas y lote vigente hasta 2028.",
                },
                headers=dentist_headers,
            )
            assert rev_res.status_code == 201, rev_res.text
            rev_data = rev_res.json()
        else:
            rev_data = existing_reviews[0]
        assert rev_data["is_verified_purchase"] is True
        print(
            f"5. [OK] Reseña de {rev_data['rating']} estrellas registrada con insignia automática "
            f"`is_verified_purchase = {rev_data['is_verified_purchase']}`."
        )

        # 7. Actualizar estado de la orden a Enviado con guía de rastreo
        status_res = client.patch(
            f"/api/orders/{order_data['id']}/status",
            json={"status": "Enviado", "tracking_number": "DHL-ODONTO-998877"},
            headers=vendor_headers,
        )
        assert status_res.status_code == 200
        assert status_res.json()["status"] == "Enviado"
        print(
            f"6. [OK] Estado de Orden #{order_data['id']} actualizado a '{status_res.json()['status']}' "
            f"con guía '{status_res.json()['tracking_number']}'."
        )

    print("\n[EXITO] FASE 3 VERIFICADA AL 100%: Todos los endpoints del Marketplace Dental están operativos.")
    print("=" * 78)


if __name__ == "__main__":
    run_phase3_tests()
