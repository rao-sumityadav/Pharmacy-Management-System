from datetime import datetime, date, timedelta
from app import create_app
from models import (
    db, User, Medicine, Supplier, Customer, Bill, BillItem, 
    Payment, PurchaseOrder, MedicineReturn, Reservation, Prescription
)

app = create_app()

def seed_database():
    with app.app_context():
        # Clear existing tables
        db.drop_all()
        db.create_all()

        print("Creating User Accounts...")
        # 1. Users (Admin + Pharmacist)
        admin = User(
            user_code="ADM-1001",
            name="Dr. Vikram Malhotra",
            email="admin@pharmacy.com",
            role="admin",
            phone="+91 9876543210",
            address="102 Medical Enclave, Main Road, New Delhi",
            shop_name="PharmaCare Chemists & Druggists",
            is_active=True
        )
        admin.set_password("admin123")

        pharmacist = User(
            user_code="PHR-2001",
            name="Suresh Verma",
            email="pharmacist@pharmacy.com",
            role="pharmacist",
            phone="+91 9812345678",
            address="Flat 4B, Green Park Extension, New Delhi",
            shop_name="PharmaCare Chemists & Druggists",
            is_active=True
        )
        pharmacist.set_password("pharma123")

        db.session.add_all([admin, pharmacist])
        db.session.commit()

        print("Creating Suppliers...")
        # 2. Suppliers
        s1 = Supplier(
            supplier_code="SUP-001",
            name="Apex Healthcare Distributors",
            contact_number="+91 9823456789",
            email="orders@apexhealth.com",
            address="Plot 12, Industrial Area Phase 1, New Delhi",
            supplied_medicines="Antibiotics, Antipyretics, Cardiovascular"
        )
        s2 = Supplier(
            supplier_code="SUP-002",
            name="Global Meds Wholesale Logistics",
            contact_number="+91 9123456780",
            email="supply@globalmeds.in",
            address="Warehouse 5B, Bhiwandi Logistics Park, Mumbai",
            supplied_medicines="Analgesics, Gastrointestinal, Antacids, Respiratory"
        )
        s3 = Supplier(
            supplier_code="SUP-003",
            name="LifeLine Pharma Supply",
            contact_number="+91 9988776655",
            email="contact@lifelinesupply.com",
            address="7th Cross, Electronic City, Bangalore",
            supplied_medicines="Vitamins, Hormonal, Dermatology, Pediatric"
        )
        db.session.add_all([s1, s2, s3])
        db.session.commit()

        print("Creating 22 Sample Medicines...")
        today = date.today()

        medicines_data = [
            # Antibiotics
            ("MED-001", "Amoxicillin 500mg", "Amoxicillin Trihydrate", "Antibiotics", "AMX-801", 45, 12.50, 7.80, "Cipla Ltd", today - timedelta(days=180), today + timedelta(days=365), 10, "Rack A-01"),
            ("MED-002", "Azithromycin 250mg", "Azithromycin", "Antibiotics", "AZI-102", 8, 22.00, 14.50, "Sun Pharma", today - timedelta(days=120), today + timedelta(days=400), 10, "Rack A-02"),
            ("MED-003", "Ciprofloxacin 500mg", "Ciprofloxacin HCl", "Antibiotics", "CIP-304", 0, 18.00, 11.20, "Alkem Labs", today - timedelta(days=200), today + timedelta(days=300), 10, "Rack A-03"),
            ("MED-004", "Doxycycline 100mg", "Doxycycline Hyclate", "Antibiotics", "DOX-405", 30, 8.50, 4.90, "Dr. Reddy's", today - timedelta(days=150), today + timedelta(days=450), 10, "Rack A-04"),
            
            # Analgesics & Antipyretics
            ("MED-005", "Paracetamol 650mg", "Acetaminophen", "Analgesics", "PCM-901", 120, 3.50, 1.80, "Micro Labs (Dolo)", today - timedelta(days=90), today + timedelta(days=550), 20, "Rack B-01"),
            ("MED-006", "Ibuprofen 400mg", "Ibuprofen", "Analgesics", "IBU-502", 60, 4.80, 2.70, "Abbott India", today - timedelta(days=100), today + timedelta(days=500), 15, "Rack B-02"),
            ("MED-007", "Tramadol 50mg", "Tramadol HCl", "Analgesics", "TRM-201", 25, 15.00, 9.00, "Cadila Pharma", today - timedelta(days=80), today + timedelta(days=420), 10, "Rack B-03"),
            ("MED-008", "Diclofenac 50mg", "Diclofenac Sodium", "Analgesics", "DIC-603", 5, 6.00, 3.20, "Novartis India", today - timedelta(days=140), today + timedelta(days=360), 10, "Rack B-04"),

            # Cardiovascular & Antidiabetics
            ("MED-009", "Metformin 500mg", "Metformin HCl", "Antidiabetic", "MET-701", 85, 4.00, 2.10, "USV Pvt Ltd", today - timedelta(days=110), today + timedelta(days=600), 15, "Rack C-01"),
            ("MED-010", "Glimepiride 2mg", "Glimepiride", "Antidiabetic", "GLI-802", 35, 7.50, 4.20, "Sanofi India", today - timedelta(days=95), today + timedelta(days=520), 10, "Rack C-02"),
            ("MED-011", "Amlodipine 5mg", "Amlodipine Besylate", "Cardiovascular", "AML-903", 50, 5.00, 2.60, "Torrent Pharma", today - timedelta(days=130), today + timedelta(days=480), 15, "Rack C-03"),
            ("MED-012", "Telmisartan 40mg", "Telmisartan", "Cardiovascular", "TEL-104", 40, 9.20, 5.30, "Glenmark", today - timedelta(days=100), today + timedelta(days=490), 10, "Rack C-04"),
            ("MED-013", "Atorvastatin 20mg", "Atorvastatin Calcium", "Cardiovascular", "ATO-205", 0, 16.50, 10.00, "Lupin Ltd", today - timedelta(days=150), today + timedelta(days=380), 10, "Rack C-05"),

            # Gastrointestinal & Antacids
            ("MED-014", "Pantoprazole 40mg", "Pantoprazole Sodium", "Gastrointestinal", "PAN-301", 90, 8.00, 4.50, "Aristo Pharma", today - timedelta(days=70), today + timedelta(days=530), 15, "Rack D-01"),
            ("MED-015", "Omeprazole 20mg", "Omeprazole", "Gastrointestinal", "OME-402", 6, 6.50, 3.40, "Cipla Ltd", today - timedelta(days=110), today + timedelta(days=410), 10, "Rack D-02"),
            ("MED-016", "Ondansetron 4mg", "Ondansetron HCl", "Gastrointestinal", "OND-503", 24, 7.00, 3.80, "GlaxoSmithKline", today - timedelta(days=90), today + timedelta(days=390), 10, "Rack D-03"),

            # Respiratory & Antihistamines
            ("MED-017", "Cetirizine 10mg", "Cetirizine Di-HCl", "Respiratory", "CET-601", 110, 3.00, 1.40, "Dr. Reddy's", today - timedelta(days=80), today + timedelta(days=620), 20, "Rack E-01"),
            ("MED-018", "Montelukast 10mg", "Montelukast Sodium", "Respiratory", "MON-702", 40, 14.00, 8.20, "Sun Pharma", today - timedelta(days=100), today + timedelta(days=450), 10, "Rack E-02"),

            # Nearing Expiry (< 30 days)
            ("MED-019", "Cefixime 200mg", "Cefixime Trihydrate", "Antibiotics", "CFX-901", 15, 19.50, 12.00, "Zydus Healthcare", today - timedelta(days=330), today + timedelta(days=14), 10, "Rack E-03"),
            ("MED-020", "Erythromycin 250mg", "Erythromycin Stearate", "Antibiotics", "ERY-410", 12, 11.00, 6.50, "Alembic Pharma", today - timedelta(days=340), today + timedelta(days=22), 10, "Rack E-04"),

            # Already Expired (Strictly Blocked from Sale)
            ("MED-021", "Tetracycline 250mg", "Tetracycline HCl", "Antibiotics", "TET-119", 14, 9.00, 5.00, "Pfizer India", today - timedelta(days=400), today - timedelta(days=15), 10, "Quarantine Bay"),
            ("MED-022", "Ampicillin 500mg", "Ampicillin Sodium", "Antibiotics", "AMP-055", 20, 10.50, 6.00, "Ranbaxy", today - timedelta(days=450), today - timedelta(days=45), 10, "Quarantine Bay")
        ]

        created_medicines = []
        for code, name, gen, cat, batch, qty, price, cost, mfg, mfg_date, exp_date, threshold, rack in medicines_data:
            m = Medicine(
                medicine_code=code,
                name=name,
                generic_name=gen,
                category=cat,
                batch_number=batch,
                quantity=qty,
                unit_price=price,
                cost_price=cost,
                manufacturer=mfg,
                manufacturing_date=mfg_date,
                expiry_date=exp_date,
                reorder_threshold=threshold,
                rack_location=rack,
                is_discontinued=False
            )
            db.session.add(m)
            created_medicines.append(m)

        db.session.commit()

        print("Creating Sample Customers...")
        # 3. Customers
        c1 = Customer(
            customer_code="CUST-101",
            name="Rajesh Kumar",
            phone_number="+91 9811122233",
            email="rajesh.kumar@gmail.com",
            address="House 42, Pocket B, Mayur Vihar, Delhi"
        )
        c2 = Customer(
            customer_code="CUST-102",
            name="Priya Sharma",
            phone_number="+91 9822233344",
            email="priya.sharma@yahoo.com",
            address="A-304, Palm Grove Apartments, Noida"
        )
        c3 = Customer(
            customer_code="CUST-103",
            name="Amit Verma",
            phone_number="+91 9833344455",
            email="amit.v@outlook.com",
            address="C-12, Sector 15, Faridabad"
        )
        db.session.add_all([c1, c2, c3])
        db.session.commit()

        print("Creating Sample Bills & Invoices...")
        # 4. Bill 1: Fully Paid Sale
        b1 = Bill(
            bill_number="INV-202609-1001",
            customer_id=c1.id,
            customer_name=c1.name,
            customer_phone=c1.phone_number,
            subtotal=235.00,
            discount_percent=5.0,
            discount_amount=11.75,
            tax_percent=5.0,
            tax_amount=11.16,
            total_amount=234.41,
            paid_amount=234.41,
            due_amount=0.0,
            status="paid",
            payment_method="upi",
            notes="Walk-in prescription order",
            created_by_id=pharmacist.id,
            created_at=datetime.utcnow() - timedelta(hours=3)
        )
        db.session.add(b1)
        db.session.flush()

        item1 = BillItem(
            bill_id=b1.id,
            medicine_id=created_medicines[4].id,  # Paracetamol
            medicine_name=created_medicines[4].name,
            batch_number=created_medicines[4].batch_number,
            quantity=10,
            unit_price=created_medicines[4].unit_price,
            cost_price=created_medicines[4].cost_price,
            subtotal=35.00
        )
        item2 = BillItem(
            bill_id=b1.id,
            medicine_id=created_medicines[0].id,  # Amoxicillin
            medicine_name=created_medicines[0].name,
            batch_number=created_medicines[0].batch_number,
            quantity=16,
            unit_price=created_medicines[0].unit_price,
            cost_price=created_medicines[0].cost_price,
            subtotal=200.00
        )
        pay1 = Payment(
            bill_id=b1.id,
            payment_method="upi",
            amount=234.41,
            payment_status="success",
            transaction_ref="UPI-REF-892173491",
            notes="GPay QR payment captured"
        )
        db.session.add_all([item1, item2, pay1])

        # Bill 2: Credit / Overdue Bill with Fine
        # Due date was 5 days ago to demonstrate Rs. 10/day fine
        overdue_due_date = today - timedelta(days=5)
        b2 = Bill(
            bill_number="INV-202609-1002",
            customer_id=c2.id,
            customer_name=c2.name,
            customer_phone=c2.phone_number,
            subtotal=450.00,
            discount_percent=0.0,
            discount_amount=0.0,
            tax_percent=5.0,
            tax_amount=22.50,
            total_amount=472.50,
            paid_amount=100.00,
            due_amount=372.50,
            due_date=overdue_due_date,
            status="partial",
            payment_method="cash",
            notes="Regular customer credit purchase",
            created_by_id=pharmacist.id,
            created_at=datetime.utcnow() - timedelta(days=20)
        )
        db.session.add(b2)
        db.session.flush()

        item3 = BillItem(
            bill_id=b2.id,
            medicine_id=created_medicines[8].id,  # Metformin
            medicine_name=created_medicines[8].name,
            batch_number=created_medicines[8].batch_number,
            quantity=30,
            unit_price=created_medicines[8].unit_price,
            cost_price=created_medicines[8].cost_price,
            subtotal=120.00
        )
        item4 = BillItem(
            bill_id=b2.id,
            medicine_id=created_medicines[11].id,  # Telmisartan
            medicine_name=created_medicines[11].name,
            batch_number=created_medicines[11].batch_number,
            quantity=30,
            unit_price=created_medicines[11].unit_price,
            cost_price=created_medicines[11].cost_price,
            subtotal=276.00
        )
        pay2 = Payment(
            bill_id=b2.id,
            payment_method="cash",
            amount=100.00,
            payment_status="success",
            transaction_ref="CASH-PARTIAL-001",
            notes="Initial cash deposit"
        )
        db.session.add_all([item3, item4, pay2])

        print("Creating Sample Purchase Orders...")
        # 5. Purchase Orders
        po1 = PurchaseOrder(
            po_number="PO-202609-001",
            supplier_id=s1.id,
            medicine_id=created_medicines[4].id,  # Paracetamol
            quantity=200,
            unit_cost=1.80,
            total_cost=360.00,
            status="received",
            order_date=today - timedelta(days=10),
            received_date=today - timedelta(days=2),
            notes="Bulk restock order",
            created_by_id=admin.id
        )
        po2 = PurchaseOrder(
            po_number="PO-202609-002",
            supplier_id=s2.id,
            medicine_id=created_medicines[2].id,  # Ciprofloxacin (0 stock)
            quantity=50,
            unit_cost=11.20,
            total_cost=560.00,
            status="ordered",
            order_date=today - timedelta(days=1),
            notes="Urgent replenishment for out-of-stock medicine",
            created_by_id=admin.id
        )
        db.session.add_all([po1, po2])

        print("Creating Returns with Quality Verification...")
        # 6. Returns
        ret1 = MedicineReturn(
            return_number="RET-202609-001",
            bill_id=b1.id,
            medicine_id=created_medicines[0].id,
            quantity=2,
            refund_amount=25.00,
            return_reason="Doctor changed dosage from 500mg to 250mg",
            quality_status="pending_verification",
            created_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.session.add(ret1)

        print("Creating Customer Backorders / Reservations...")
        # 7. Reservations
        res1 = Reservation(
            reservation_number="RES-202609-001",
            medicine_id=created_medicines[2].id,  # Ciprofloxacin (out of stock)
            customer_name="Sunil Mehra",
            customer_phone="+91 9911223344",
            customer_email="sunil.mehra@gmail.com",
            quantity=2,
            status="pending",
            notes="Needed for 7-day course. Please call upon arrival.",
            created_at=datetime.utcnow() - timedelta(days=1)
        )
        db.session.add(res1)

        print("Creating Sample E-Prescriptions...")
        # 8. Prescription Upload
        rx1 = Prescription(
            rx_number="RX-202609-001",
            customer_name="Anita Deshmukh",
            customer_phone="+91 9876501234",
            customer_email="anita.d@gmail.com",
            file_path="sample_rx.png",
            notes="Prescription from Dr. Kapoor (Cardiologist) for blood pressure control",
            status="pending",
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
        db.session.add(rx1)

        db.session.commit()
        print("\n=======================================================")
        print("  Database seeded successfully with realistic data!")
        print("=======================================================")
        print(f"  Admin:       admin@pharmacy.com      (pwd: admin123)")
        print(f"  Pharmacist:  pharmacist@pharmacy.com (pwd: pharma123)")
        print(f"  Total Meds:  {len(medicines_data)}")
        print(f"  Suppliers:   3")
        print(f"  Customers:   3")
        print(f"  Sample Bills: 2 (1 Paid, 1 Overdue Credit with Fine)")
        print("=======================================================\n")

if __name__ == "__main__":
    seed_database()
