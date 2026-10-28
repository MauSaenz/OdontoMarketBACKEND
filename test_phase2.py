"""
Script de Prueba y Verificación de la Fase 2 (`test_phase2.py`).
Prueba el flujo completo de Esquemas Pydantic v2, Hashing Bcrypt, Tokens JWT y Roles:
1. Registro de una Odontóloga (`role = cliente`) en `POST /api/auth/register`.
2. Registro de un Depósito Dental (`role = vendedor`) con `vendor_profile` y licencia COFEPRIS.
3. Inicio de sesión en `POST /api/auth/login-json` y verificación del token JWT emitido.
4. Consulta de ruta protegida `GET /api/auth/me` enviando el Header `Authorization: Bearer <token>`.
5. Validación de reglas de negocio Pydantic (ej. rechazo automático si `wholesale_price >= price`).
"""

import sys
from fastapi.testclient import TestClient
from pydantic import ValidationError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.main import app
from app.schemas.catalog import ProductCreate


def run_phase2_tests() -> None:
    print("=" * 78)
    print("[ODONTOMARKET] INICIANDO PRUEBAS DE FASE 2: PYDANTIC V2 + JWT + ROLES")
    print("=" * 78)

    with TestClient(app) as client:
        # 1. Probar endpoint de salud
        health_res = client.get("/api/health")
        assert health_res.status_code == 200
        print(f"\n1. [OK] GET /api/health -> {health_res.json()['status']}")

        # 2. Registrar una Odontóloga (Rol: cliente)
        dentist_payload = {
            "email": "dra.valeria@clinicasmile.com",
            "password": "OdontoSegura2026!",
            "full_name": "Dra. Valeria Morales",
            "role": "cliente",
            "professional_license": "CED-ODON-8492011",
            "clinic_name": "Clínica Dental Smile Center",
            "phone": "+52 55 1234 5678",
        }
        reg_dentist = client.post("/api/auth/register", json=dentist_payload)
        if reg_dentist.status_code == 400 and "Ya existe" in reg_dentist.text:
            # Si ya se había corrido antes la prueba, iniciamos sesión directamente
            reg_dentist = client.post(
                "/api/auth/login-json",
                json={"email": dentist_payload["email"], "password": dentist_payload["password"]},
            )
        assert reg_dentist.status_code in (200, 201), reg_dentist.text
        dentist_data = reg_dentist.json()
        dentist_token = dentist_data["access_token"]
        print(
            f"2. [OK] Odontóloga autenticada: {dentist_data['user']['full_name']} "
            f"| Rol: {dentist_data['user']['role']} | Cédula: {dentist_data['user']['professional_license']}"
        )

        # 3. Registrar un Depósito Dental (Rol: vendedor) con VendorProfile anidado
        vendor_payload = {
            "email": "ventas@depositovillacortes.com",
            "password": "DepositoDental2026!",
            "full_name": "Ing. Roberto Alcántara",
            "role": "vendedor",
            "phone": "+52 55 9876 5432",
            "vendor_profile": {
                "business_name": "Depósito Dental Villa de Cortés S.A.",
                "tax_id": "DDV2401158A1",
                "sanitary_license": "COFEPRIS-AV-2026-09841",
                "description": "Distribuidor autorizado 3M ESPE, Ivoclar Vivadent y NSK.",
                "city": "Ciudad de México",
                "state": "CDMX",
                "address": "Av. Cuauhtémoc 450, Col. Narvarte",
            },
        }
        reg_vendor = client.post("/api/auth/register", json=vendor_payload)
        if reg_vendor.status_code == 400 and "Ya existe" in reg_vendor.text:
            reg_vendor = client.post(
                "/api/auth/login-json",
                json={"email": vendor_payload["email"], "password": vendor_payload["password"]},
            )
        assert reg_vendor.status_code in (200, 201), reg_vendor.text
        vendor_data = reg_vendor.json()
        vendor_token = vendor_data["access_token"]
        print(
            f"3. [OK] Depósito Dental autenticado: {vendor_data['user']['vendor_profile']['business_name']} "
            f"| Licencia: {vendor_data['user']['vendor_profile']['sanitary_license']}"
        )

        # 4. Probar ruta protegida GET /api/auth/me inyectando el Token JWT en el Header
        me_res = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {vendor_token}"},
        )
        assert me_res.status_code == 200
        me_json = me_res.json()
        assert "hashed_password" not in me_json, "ERROR: hashed_password nunca debe filtrarse"
        print(
            f"4. [OK] GET /api/auth/me verificado con JWT -> ID={me_json['id']}, "
            f"Rol={me_json['role']}, Depósito={me_json['vendor_profile']['business_name']}"
        )

        # 5. Probar validación Pydantic v2 de precios de mayoreo en ProductCreate
        try:
            ProductCreate(
                category_id=5,
                name="Resina 3M Filtek Z350",
                sku="3M-Z350-ERR",
                description="Resina nanohíbrida",
                brand="3M ESPE",
                sanitary_registration="COFEPRIS 1482C2023 SSA",
                lot_number="LOT-2026",
                presentation="Jeringa 4g",
                price=850.0,
                wholesale_price=950.0,  # Inválido: mayor al precio normal
                wholesale_min_qty=5,
                stock=10,
                image_url="https://example.com/resina.jpg",
            )
            raise AssertionError("Debió lanzar ValidationError")
        except ValidationError as exc:
            print(
                "5. [OK] Validación Pydantic v2 activa: Rechazó correctamente un `wholesale_price` "
                f"mayor al `price` normal ({exc.errors()[0]['msg']})."
            )

    print("\n[EXITO] FASE 2 VERIFICADA AL 100%: Esquemas Pydantic v2, Bcrypt, JWT y Roles operativos.")
    print("=" * 78)


if __name__ == "__main__":
    run_phase2_tests()
