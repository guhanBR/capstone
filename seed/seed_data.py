import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.address import Address
from app.models.cart import Cart
from app.models.order import Order, OrderItem
from app.models.review import Review
from app.models.inventory import InventoryTransaction
from app.models.notification import Notification
from app.models.audit_log import AuditLog

def seed():
    app = create_app('development')
    with app.app_context():
        print("[Seeding] Resetting database tables...")
        db.drop_all()
        db.create_all()

        print("[Seeding] Creating Admin Account...")
        admin = User(
            name="System Administrator",
            email="admin@sparepro.local",
            phone="9998887770",
            role="admin",
            status="active",
            theme_preference="dark"
        )
        admin.set_password("Admin@12345")
        db.session.add(admin)

        print("[Seeding] Creating Customer Accounts...")
        cust1 = User(
            name="Rajesh Kumar",
            email="rajesh.kumar@example.com",
            phone="9876543210",
            role="customer",
            status="active",
            theme_preference="dark"
        )
        cust1.set_password("Customer@123")

        cust2 = User(
            name="Suresh Patel",
            email="suresh.patel@example.com",
            phone="9876543211",
            role="customer",
            status="active",
            theme_preference="light"
        )
        cust2.set_password("Customer@123")

        cust3 = User(
            name="Anish Sharma",
            email="anish.sharma@example.com",
            phone="9876543212",
            role="customer",
            status="active",
            theme_preference="dark"
        )
        cust3.set_password("Customer@123")

        db.session.add_all([cust1, cust2, cust3])
        db.session.flush()

        # Carts for customers
        for c in [cust1, cust2, cust3]:
            db.session.add(Cart(user_id=c.id))

        # Sample Delivery Addresses
        addr1 = Address(
            user_id=cust1.id,
            full_name="Rajesh Kumar (Pump Works)",
            phone="9876543210",
            address_line_1="Plot 45, Phase III, Industrial Estate",
            address_line_2="Near State Electricity Board",
            city="Coimbatore",
            state="Tamil Nadu",
            postal_code="641006",
            country="India",
            is_default=True
        )

        addr2 = Address(
            user_id=cust2.id,
            full_name="Suresh Patel",
            phone="9876543211",
            address_line_1="Building 12, GIDC Industrial Park",
            address_line_2="Makarpura",
            city="Vadodara",
            state="Gujarat",
            postal_code="390010",
            country="India",
            is_default=True
        )
        db.session.add_all([addr1, addr2])

        print("[Seeding] Creating Categories...")
        categories_data = [
            ("Bearings", "High precision deep groove, angular contact & roller bearings for motor rotors and pump shafts."),
            ("Mechanical Seals", "Single spring, cartridge, ceramic & tungsten carbide seals for industrial pumps."),
            ("Capacitors", "Motor run & start capacitors engineered for continuous duty operation."),
            ("Impellers", "Cast iron, bronze, and stainless steel impellers for centrifugal & submersible pumps."),
            ("Pump Shafts", "Precision ground SS-304 & SS-316 pump drive shafts."),
            ("Motor Parts", "Cooling fans, terminal boards, junction boxes, and rotors for electric motors."),
            ("Gaskets", "EPDM, Nitrile rubber, and asbestos-free flange gaskets."),
            ("Couplings", "Lovejoy flexible jaw couplings, pin bush couplings & spider inserts."),
            ("Electrical Components", "Overload thermal relays, contactors & centrifugal switches."),
            ("Fasteners & Hardware", "High tensile Grade 8.8 bolts, circlips, keys & hardware.")
        ]

        cat_objs = {}
        for name, desc in categories_data:
            cat = Category(name=name, description=desc, status="active")
            db.session.add(cat)
            db.session.flush()
            cat_objs[name] = cat

        print("[Seeding] Creating 42 Motor & Pump Spare Parts...")
        products_data = [
            # Bearings
            ("6203 Deep Groove Ball Bearing", "BRG-6203-OPEN", "SKF", "6203", "Open deep groove ball bearing 17mm x 40mm x 12mm.", "ID: 17mm, OD: 40mm, Width: 12mm", "Fits standard 1 HP electric motors", 180.00, 160.00, 45, 10, "Bearings"),
            ("6203-2RS Rubber Sealed Ball Bearing", "BRG-6203-2RS", "SKF", "6203-2RS", "Dual rubber sealed deep groove ball bearing for moisture protection.", "ID: 17mm, OD: 40mm, Rubber Seals", "Fits 1 HP water pump motors", 220.00, 195.00, 30, 8, "Bearings"),
            ("6203-ZZ Metal Shielded Ball Bearing", "BRG-6203-ZZ", "FAG", "6203-ZZ", "Dual metal shielded ball bearing for dust resistance.", "ID: 17mm, OD: 40mm, Metal Shields", "1 HP Motor non-drive end", 210.00, 190.00, 25, 5, "Bearings"),
            ("6204 Deep Groove Ball Bearing", "BRG-6204-OPEN", "SKF", "6204", "Heavy duty bearing 20mm x 47mm x 14mm.", "ID: 20mm, OD: 47mm, Width: 14mm", "2 HP electric motor drive end", 260.00, 240.00, 40, 10, "Bearings"),
            ("6204-2RS Dual Sealed Ball Bearing", "BRG-6204-2RS", "FAG", "6204-2RS", "Rubber sealed bearing 20mm shaft.", "ID: 20mm, OD: 47mm, Dual 2RS", "2 HP Submersible pump shaft", 290.00, 270.00, 18, 5, "Bearings"),
            ("6205 Heavy Duty Ball Bearing", "BRG-6205-OPEN", "SKF", "6205", "30mm shaft ball bearing for 3 HP to 5 HP motors.", "ID: 25mm, OD: 52mm, Width: 15mm", "3 HP - 5 HP Industrial Motors", 350.00, 320.00, 50, 10, "Bearings"),
            ("6306 High Speed Motor Bearing", "BRG-6306-OPEN", "NTN", "6306", "Extra load capacity motor bearing.", "ID: 30mm, OD: 72mm, Width: 19mm", "7.5 HP Industrial Pump Motors", 580.00, 530.00, 12, 4, "Bearings"),
            
            # Mechanical Seals
            ("25mm Mechanical Seal", "SEAL-25-STD", "Burgmann", "MS-25", "Standard elastomer bellow mechanical seal for water pumps.", "Shaft Dia: 25mm, Carbon vs Ceramic", "1 HP - 2 HP Centrifugal Water Pumps", 450.00, 420.00, 20, 5, "Mechanical Seals"),
            ("25mm Premium Mechanical Seal", "SEAL-25-PREM", "Burgmann", "MS-25-P", "High durability silicon carbide mechanical seal.", "Shaft Dia: 25mm, SiC vs SiC", "Chemical & Slurry Pumps 25mm", 750.00, 690.00, 15, 5, "Mechanical Seals"),
            ("25mm Ceramic Mechanical Seal", "SEAL-25-CER", "EagleBurg", "MS-25-C", "High temperature ceramic mechanical seal.", "Shaft Dia: 25mm, Temp up to 120°C", "Hot water circulation pumps", 620.00, 580.00, 10, 3, "Mechanical Seals"),
            ("32mm Industrial Mechanical Seal", "SEAL-32-STD", "Burgmann", "MS-32", "Heavy industrial pump mechanical shaft seal.", "Shaft Dia: 32mm, Viton O-rings", "5 HP - 10 HP Industrial Water Pumps", 950.00, 880.00, 8, 3, "Mechanical Seals"),
            ("19mm Submersible Pump Seal", "SEAL-19-SUB", "Triton", "MS-19", "Dual spring submersible pump mechanical seal.", "Shaft Dia: 19mm, Oil chamber design", "Openwell & Borewell Submersibles", 510.00, 470.00, 22, 5, "Mechanical Seals"),

            # Capacitors
            ("1 HP Motor Run Capacitor 36 MFD", "CAP-36MFD-450", "Tibcon", "36MFD", "36 MFD 440VAC motor run capacitor.", "Capacitance: 36uF ±5%, 440VAC", "1 HP Single Phase Motors", 280.00, 250.00, 60, 15, "Capacitors"),
            ("2 HP Motor Run Capacitor 50 MFD", "CAP-50MFD-450", "Tibcon", "50MFD", "50 MFD heavy duty motor run capacitor.", "Capacitance: 50uF ±5%, 440VAC", "2 HP Monoblock Water Pumps", 340.00, 310.00, 40, 10, "Capacitors"),
            ("3 HP Motor Run Capacitor 72 MFD", "CAP-72MFD-450", "Keltron", "72MFD", "72 MFD high torque run capacitor.", "Capacitance: 72uF, 440VAC, Aluminum can", "3 HP Submersible Pump Control Panel", 460.00, 420.00, 25, 8, "Capacitors"),
            ("Motor Start Capacitor 120-150 MFD", "CAP-120-150", "Tibcon", "SC-150", "High starting torque motor start capacitor.", "120-150 MFD, 275VAC dry electrolytic", "Single Phase Compressor & Pump Motors", 390.00, 350.00, 35, 10, "Capacitors"),

            # Impellers
            ("Pump Impeller 100mm Bronze", "IMP-100-BRZ", "Kirloskar", "IMP-100", "100mm outer diameter cast bronze closed impeller.", "OD: 100mm, Bore: 16mm, Bronze", "1 HP Centrifugal Monoblock Pump", 1250.00, 1150.00, 14, 4, "Impellers"),
            ("Pump Impeller 125mm Cast Iron", "IMP-125-CI", "Crompton", "IMP-125", "125mm cast iron high head impeller.", "OD: 125mm, Bore: 19mm, Cast Iron", "2 HP Agricultural Monoblock Pump", 1450.00, 1350.00, 18, 5, "Impellers"),
            ("Pump Impeller 140mm Stainless Steel", "IMP-140-SS", "Grundfos", "IMP-140-SS", "SS-304 laser balanced centrifugal impeller.", "OD: 140mm, Bore: 22mm, SS-304", "Corrosive liquid & dewatering pumps", 2400.00, 2200.00, 6, 2, "Impellers"),
            ("Submersible Bowl Impeller Noryl", "IMP-SUB-NORYL", "Texmo", "IMP-SUB-4", "Glass filled Noryl stage impeller for 4-inch borewell.", "4-inch Borewell, Hex shaft drive", "1 HP 10-Stage Borewell Submersible", 420.00, 380.00, 50, 10, "Impellers"),

            # Pump Shafts
            ("Pump Shaft 16mm SS-304", "SFT-16-SS304", "LocalCraft", "SFT-16", "16mm precision turned stainless steel drive shaft.", "Diameter: 16mm, Length: 350mm, SS304", "1 HP Monoblock Pump Assembly", 890.00, 820.00, 16, 4, "Pump Shafts"),
            ("Pump Shaft 20mm SS-316", "SFT-20-SS316", "LocalCraft", "SFT-20", "20mm acid resistant SS-316 pump shaft.", "Diameter: 20mm, Length: 450mm, SS316", "2 HP - 3 HP Chemical & Water Pumps", 1450.00, 1320.00, 10, 3, "Pump Shafts"),
            ("Submersible Hex Drive Shaft 14mm", "SFT-14-HEX", "Texmo", "SFT-HEX-14", "Stainless steel hexagonal drive shaft.", "Hex Size: 14mm, Length: 900mm", "4-inch Submersible Pump Stack", 1120.00, 990.00, 12, 3, "Pump Shafts"),

            # Motor Parts
            ("Motor Cooling Fan 1 HP", "FAN-MOTOR-1HP", "Crompton", "FAN-1HP", "Polypropylene motor cooling fan blade.", "Bore: 16mm, Shaft fit, 6 Blades", "1 HP Frame 80 Motor", 150.00, 130.00, 40, 10, "Motor Parts"),
            ("Motor Cooling Fan 3 HP", "FAN-MOTOR-3HP", "ABB", "FAN-3HP", "Heavy nylon cooling fan for 3 HP motor.", "Bore: 24mm, Shaft fit, 8 Blades", "3 HP Frame 100 Motor", 240.00, 210.00, 25, 8, "Motor Parts"),
            ("Motor Terminal Block 6-Pin", "TRM-BLK-6PIN", "Siemens", "TB-6", "Bakelite 6-pin motor terminal board.", "Rating: 500V 30A, 6-Stud M5", "0.5 HP - 3 HP 3-Phase Motors", 180.00, 160.00, 55, 12, "Motor Parts"),
            ("Motor Junction Box Cover", "JNC-BOX-CVR", "Havells", "JBC-01", "Die-cast aluminum junction box with gasket.", "Frame Size: IEC 90/100, IP55 rated", "Standard TEFC Electric Motors", 320.00, 290.00, 20, 5, "Motor Parts"),
            ("Centrifugal Switch Assembly 1 HP", "CSW-1HP-2P", "Crompton", "CSW-1", "Centrifugal switch governor mechanism for single phase motors.", "2-Pole 3000 RPM, 16mm shaft bore", "1 HP CSCR Single Phase Motors", 340.00, 300.00, 28, 6, "Motor Parts"),

            # Gaskets
            ("Rubber Flange Gasket 50mm (2 inch)", "GSK-50MM-RUB", "Flexitallic", "GSK-50", "3mm Neoprene rubber flange gasket.", "ID: 60mm, OD: 105mm, 4 Bolt Holes", "2 inch Pump Suction/Delivery Flange", 65.00, 55.00, 100, 20, "Gaskets"),
            ("Pump Casing O-Ring Nitrile", "GSK-ORING-CAS", "Precision", "OR-CAS-180", "Nitrile rubber casing O-ring seal.", "ID: 180mm, Thickness: 4mm, NBR 70", "Monoblock Pump Casing Seal", 95.00, 85.00, 80, 15, "Gaskets"),
            ("Asbestos-Free Sheet Gasket 80mm", "GSK-80MM-AF", "Champion", "AF-80", "High pressure non-asbestos jointing gasket.", "Size: 3 inch Flange, 150 PSI rated", "Industrial Water Pipe Flanges", 140.00, 120.00, 50, 10, "Gaskets"),

            # Couplings
            ("Motor Coupling L-095 Lovejoy", "CPL-L095-SET", "Lovejoy", "L-095", "Flexible jaw coupling set with NBR spider insert.", "Bore Range: 14mm to 28mm, Torque 20 Nm", "Motor to Pump Direct Drive", 850.00, 780.00, 18, 5, "Couplings"),
            ("Lovejoy Spider Insert L-095 NBR", "CPL-L095-SPDR", "Lovejoy", "L-095-SP", "Nitrile rubber replacement spider cushion.", "Fits L-095 Jaw Couplings", "Spare insert for L-095 coupling", 180.00, 160.00, 45, 10, "Couplings"),
            ("Pin Bush Flexible Coupling F-4", "CPL-PIN-F4", "Fenner", "F-4", "Cast iron pin bush flexible coupling.", "Max Bore: 38mm, 4 Rubber Bushes", "10 HP Motor Heavy Duty Drive", 1850.00, 1680.00, 6, 2, "Couplings"),

            # Electrical Components
            ("Thermal Overload Relay 9-13A", "ELC-TOR-9-13A", "L&T", "MN2-13", "Bimetallic thermal overload protection relay.", "Setting Range: 9A - 13A, 1NO + 1NC", "Direct-On-Line (DOL) Motor Starter", 720.00, 650.00, 24, 6, "Electrical Components"),
            ("3-Pole AC Contactor 18A", "ELC-CNT-18A", "Schneider", "LC1D18", "3-Pole 415V AC power contactor.", "Current: 18A AC-3, Coil 220V/415V", "Motor Control Starters & Panels", 1150.00, 1050.00, 16, 4, "Electrical Components"),
            ("Single Phase Preventer Relay", "ELC-SPP-415V", "Minilec", "SPP-01", "Phase failure and reverse phase protection relay.", "Voltage: 415V 3-Phase, Auto reset", "3-Phase Submersible & Motor Starters", 850.00, 780.00, 20, 5, "Electrical Components"),

            # Fasteners & Hardware
            ("SS-304 Impeller Nut M12", "FST-NUT-M12-SS", "Unbrako", "M12-SS", "Stainless steel dome lock nut for pump impellers.", "Thread: M12 x 1.75, SS-304 Left/Right", "Securing Impellers on Pump Shafts", 35.00, 30.00, 200, 40, "Fasteners & Hardware"),
            ("High Tensile Motor Bolts M8 x 40", "FST-BLT-M8-40", "Unbrako", "M8x40-8.8", "Grade 8.8 hex head motor body bolts (Pack of 10).", "M8 x 40mm, Zinc Plated, 10 Pcs", "Motor end-shield & casing assembly", 120.00, 100.00, 60, 15, "Fasteners & Hardware"),
            ("Shaft Key SS-304 6mm x 6mm x 30mm", "FST-KEY-6X6X30", "LocalCraft", "KEY-6x6", "Precision parallel drive key SS-304.", "6mm x 6mm x 30mm, DIN 6885A", "Keyway fit for shafts and pulleys", 45.00, 40.00, 150, 30, "Fasteners & Hardware"),
            ("External Circlip for 20mm Shaft", "FST-CIR-20MM", "Norma", "CIR-20", "Spring steel shaft retaining ring (Pack of 10).", "Shaft Dia: 20mm, Spring Steel", "Bearing retaining on motor shafts", 80.00, 70.00, 90, 20, "Fasteners & Hardware"),
            ("Water Pump Mechanical Seal Lubricant", "LUB-SEAL-GREASE", "Molykote", "LUB-100", "Food-grade silicone grease for O-rings & seals.", "100g Tube, Temp -40°C to 200°C", "Assembly lube for mechanical seals", 350.00, 310.00, 30, 8, "Fasteners & Hardware")
        ]

        sku_image_map = {
            "BRG-6203-OPEN": "bearings/6203-bearing.jpg",
            "BRG-6203-2RS": "bearings/6203-2rs.jpg",
            "BRG-6203-ZZ": "bearings/6203-zz.jpg",
            "BRG-6204-OPEN": "bearings/6204.jpg",
            "BRG-6204-2RS": "bearings/6204-2rs.jpg",
            "BRG-6205-OPEN": "bearings/6205.jpg",
            "BRG-6306-OPEN": "bearings/6306.jpg",

            "SEAL-25-STD": "mechanical-seals/seal-25mm.jpg",
            "SEAL-25-PREM": "mechanical-seals/seal-25mm-prem.jpg",
            "SEAL-25-CER": "mechanical-seals/seal-ceramic.jpg",
            "SEAL-32-STD": "mechanical-seals/seal-32mm.jpg",
            "SEAL-19-SUB": "mechanical-seals/seal-19mm-sub.jpg",

            "CAP-36MFD-450": "capacitors/cap-36mfd.jpg",
            "CAP-50MFD-450": "capacitors/cap-50mfd.jpg",
            "CAP-72MFD-450": "capacitors/cap-72mfd.jpg",
            "CAP-120-150": "capacitors/cap-150mfd.jpg",

            "IMP-100-BRZ": "impellers/impeller-100mm-bronze.jpg",
            "IMP-125-CI": "impellers/impeller-125mm-ci.jpg",
            "IMP-140-SS": "impellers/impeller-140mm-ss.jpg",
            "IMP-SUB-NORYL": "impellers/impeller-noryl.jpg",

            "SFT-16-SS304": "pump-shafts/shaft-16mm.jpg",
            "SFT-20-SS316": "pump-shafts/shaft-20mm.jpg",
            "SFT-14-HEX": "pump-shafts/shaft-14mm-hex.jpg",

            "FAN-MOTOR-1HP": "motor-parts/fan-1hp.jpg",
            "FAN-MOTOR-3HP": "motor-parts/fan-3hp.jpg",
            "TRM-BLK-6PIN": "motor-parts/terminal-block-6pin.jpg",
            "JNC-BOX-CVR": "motor-parts/junction-box.jpg",
            "CSW-1HP-2P": "motor-parts/centrifugal-switch.jpg",

            "GSK-50MM-RUB": "gaskets/gasket-50mm.jpg",
            "GSK-ORING-CAS": "gaskets/oring-casing.jpg",
            "GSK-80MM-AF": "gaskets/gasket-80mm-af.jpg",

            "CPL-L095-SET": "couplings/coupling-l095.jpg",
            "CPL-L095-SPDR": "couplings/spider-insert-l095.jpg",
            "CPL-PIN-F4": "couplings/pin-bush-f4.jpg",

            "ELC-TOR-9-13A": "electrical-components/thermal-relay.jpg",
            "ELC-CNT-18A": "electrical-components/ac-contactor.jpg",
            "ELC-SPP-415V": "electrical-components/phase-preventer.jpg",

            "FST-NUT-M12-SS": "fasteners/impeller-nut-m12.jpg",
            "FST-BLT-M8-40": "fasteners/motor-bolts-m8.jpg",
            "FST-KEY-6X6X30": "fasteners/shaft-key-6x6.jpg",
            "FST-CIR-20MM": "fasteners/circlip-20mm.jpg",
            "LUB-SEAL-GREASE": "fasteners/seal-grease.jpg"
        }

        products_list = []
        for name, sku, brand, model_no, desc, specs, compat, price, disc_price, stock, min_stock, cat_name in products_data:
            cat = cat_objs[cat_name]
            img_file = sku_image_map.get(sku, "placeholder.png")
            p = Product(
                category_id=cat.id,
                name=name,
                sku=sku,
                brand=brand,
                model_number=model_no,
                description=desc,
                specifications=specs,
                compatibility=compat,
                price=price,
                discount_price=disc_price,
                stock_quantity=stock,
                minimum_stock_level=min_stock,
                image=img_file,
                status="active"
            )
            db.session.add(p)
            db.session.flush()
            products_list.append(p)

            # Record initial inventory transaction for each product
            inv = InventoryTransaction(
                product_id=p.id,
                transaction_type="Purchase",
                quantity=stock,
                previous_quantity=0,
                new_quantity=stock,
                reference_type="Initial Stock",
                notes="Initial inventory import during database setup"
            )
            db.session.add(inv)

        print("[Seeding] Generating Historical Orders for Analytics...")
        # Create completed orders over past 30 days
        sample_order_data = [
            (cust1, [products_list[0], products_list[7]], 5, 2, "Delivered", "Paid", 15),
            (cust2, [products_list[1], products_list[12]], 2, 4, "Delivered", "Paid", 12),
            (cust3, [products_list[3], products_list[16]], 3, 1, "Delivered", "Paid", 8),
            (cust1, [products_list[8], products_list[20]], 1, 2, "Shipped", "Pending", 3),
            (cust2, [products_list[2], products_list[5]], 4, 3, "Processing", "Pending", 1),
            (cust3, [products_list[10], products_list[14]], 1, 1, "Pending", "Pending", 0)
        ]

        for user, item_prods, qty1, qty2, status, pay_status, days_ago in sample_order_data:
            order_date = datetime.utcnow() - timedelta(days=days_ago)
            order_num = f"SP-{order_date.strftime('%Y%m%d')}-{user.id}00{days_ago}"

            p1, p2 = item_prods[0], item_prods[1]
            subtotal = (p1.effective_price * qty1) + (p2.effective_price * qty2)
            shipping = 0.0 if subtotal >= 2000 else 100.0
            total = subtotal + shipping

            ord_obj = Order(
                user_id=user.id,
                order_number=order_num,
                address_id=user.addresses[0].id if user.addresses else None,
                subtotal=subtotal,
                discount=0.0,
                shipping_charge=shipping,
                total_amount=total,
                payment_method="Cash on Delivery",
                payment_status=pay_status,
                order_status=status,
                created_at=order_date,
                updated_at=order_date
            )
            db.session.add(ord_obj)
            db.session.flush()

            # Items
            i1 = OrderItem(order_id=ord_obj.id, product_id=p1.id, product_name=p1.name, sku=p1.sku, quantity=qty1, unit_price=p1.effective_price, subtotal=p1.effective_price * qty1, created_at=order_date)
            i2 = OrderItem(order_id=ord_obj.id, product_id=p2.id, product_name=p2.name, sku=p2.sku, quantity=qty2, unit_price=p2.effective_price, subtotal=p2.effective_price * qty2, created_at=order_date)
            db.session.add_all([i1, i2])

            # Deduct stock and log inventory sale
            for p, q in [(p1, qty1), (p2, qty2)]:
                prev_s = p.stock_quantity
                new_s = max(0, prev_s - q)
                p.stock_quantity = new_s

                inv = InventoryTransaction(
                    product_id=p.id,
                    transaction_type="Sale",
                    quantity=q,
                    previous_quantity=prev_s,
                    new_quantity=new_s,
                    reference_type="Order",
                    reference_id=ord_obj.id,
                    notes=f"Sample order {ord_obj.order_number}",
                    created_at=order_date
                )
                db.session.add(inv)

            # Sample Reviews for delivered orders
            if status == "Delivered":
                rev = Review(
                    user_id=user.id,
                    product_id=p1.id,
                    order_id=ord_obj.id,
                    rating=5,
                    review_text=f"Excellent genuine {p1.brand} part! Perfect dimensions and smooth operation on our workshop pump.",
                    status="approved",
                    created_at=order_date + timedelta(days=2)
                )
                db.session.add(rev)

        print("[Seeding] Audit logs and Notifications...")
        audit = AuditLog(
            user_id=admin.id,
            action="SEED_DATABASE",
            entity_type="System",
            description="Initial database seeding with 42 motor & pump products and sample orders completed."
        )
        db.session.add(audit)

        db.session.commit()
        print("[Seeding SUCCESS] SparePro Database populated successfully!")

if __name__ == '__main__':
    seed()
