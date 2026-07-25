# RKPR RESTAURANT CRM — PROJECT PLAN

## 1. DOCUMENT PURPOSE

This document defines the complete business, product, operational, and phased implementation plan for the RKPR Restaurant CRM. It is the central execution map for the entire project. Claude must use it together with `CLAUDE.md` and the later architecture, database, module, integration, quality, and deployment documents.

The system is a private, single-business CRM built specifically for RKPR Fast-Food Restaurant. It is not a generic SaaS CRM, no-code platform, or multi-tenant product. All restaurant information in this plan is dummy data created for development, testing, demonstrations, and seed environments. It must be clearly separated from future real client data.

**Phase numbering:** `/ROADMAP.md` is the single canonical execution sequence and status tracker (Phase 0 through Phase 19). Section 15 of this document maps the full business and functional scope described below onto that exact phase sequence. This document does not define its own phase numbering.

## 2. PROJECT OBJECTIVE

Build a high-speed, secure, production-grade restaurant CRM that gives RKPR complete control over:

- Dashboard and business visibility
- Customers and customer lifetime history
- Leads and lead conversion
- Online orders and restaurant operations
- Menu, product, ingredient, and inventory control
- Reservations and calendar workflows
- Communication across WhatsApp, email, SMS, and web channels
- Lightweight internal knowledge documents
- Staff and HR administration
- Marketing, loyalty, feedback, and retention
- Reports, analytics, and controlled AI assistance
- Integrations, security, audit logs, and operational settings

The system must remain responsive while handling large, continuously growing datasets. All collection pages must use bounded server-side pagination, filtering, sorting, indexed searches, background jobs for heavy work, and carefully scoped realtime updates.

## 3. DUMMY RESTAURANT PROFILE

### 3.1 Identity

Restaurant name: RKPR Fast-Food Restaurant

Display brand: RKPR

Legal business name: RKPR Foods & Hospitality

Business type: Quick-service fast-food restaurant

Primary cuisine: Burgers, pizzas, tacos, burritos, fries, beverages, desserts, and combo meals

Business model: Dine-in, takeaway, direct online ordering, phone ordering, aggregator ordering, and event or group orders

Dummy GSTIN: 29AABCR7428K1Z6

Dummy FSSAI licence number: 11226999000421

Dummy PAN: AABCR7428K

Dummy establishment code: RKPR-BLR-001

### 3.2 Location and contact information

Address: 18, Ground Floor, Orion Commercial Lane, 4th Block, Rajajinagar, Bengaluru, Karnataka 560010, India

Landmark: Opposite Orion East Gate, near Mahalakshmi Metro Station

Latitude: 13.0116

Longitude: 77.5550

Primary phone: +91 80 4123 7788

Reservation phone: +91 99001 77881

WhatsApp business number: +91 99001 77882

Kitchen operations phone: +91 99001 77883

Owner escalation phone: +91 99001 77884

General email: hello@rkpr-demo.example

Orders email: orders@rkpr-demo.example

Reservations email: reservations@rkpr-demo.example

Support email: support@rkpr-demo.example

Owner reports email: owner@rkpr-demo.example

Website: https://rkpr-demo.example

Instagram handle: @rkpr.demo

Facebook page: RKPR Demo Restaurant

Google Business profile identifier: RKPR-DEMO-BLR-001

All domains, emails, phone numbers, IDs, and licence values above are dummy values and must never be treated as real client information.

### 3.3 Operating hours

Monday to Thursday: 11:00 AM to 11:00 PM

Friday: 11:00 AM to 12:00 AM

Saturday: 10:30 AM to 12:00 AM

Sunday: 10:30 AM to 11:30 PM

Breakfast service: Not available initially

Lunch service: 11:00 AM to 4:00 PM

Evening service: 4:00 PM to 7:00 PM

Dinner service: 7:00 PM to closing

Last direct delivery order: 45 minutes before closing

Last dine-in order: 30 minutes before closing

Reservation approval cutoff: 60 minutes before requested time

### 3.4 Restaurant layout and capacity

Total floor area: 2,850 square feet

Indoor seating: 72 guests

Outdoor seating: 20 guests

Total normal capacity: 92 guests

Standing event capacity: 130 guests

Two-person tables: 10

Four-person tables: 12

Six-person tables: 4

Eight-person community table: 1

Outdoor four-person tables: 5

Wheelchair-accessible tables: 4

Private group zone: 18 guests

Kitchen zones: Burger line, pizza line, Mexican line, fryer station, beverage station, dessert station, packaging station, wash area, dry storage, chilled storage, frozen storage

Parking: Shared commercial parking, approximately 25 cars and 40 two-wheelers

Accessibility: Step-free entrance, accessible restroom, four accessible tables

## 4. DUMMY STAFF STRUCTURE

### 4.1 Leadership and administration

Owner: Rohan Prakash

General Manager: Kavya Rao

Operations Manager: Arjun Shetty

Finance and Admin Manager: Meera Nair

Marketing Manager: Nikhil Jain

HR and Training Coordinator: Sana Khan

### 4.2 Operational teams

Head Chef: Vivek Menon

Kitchen Supervisor: Manish Gowda

Inventory Controller: Priya Kulkarni

Reservation and Guest Relations Lead: Aditi Sharma

Customer Support Lead: Neha Bhat

Delivery Coordinator: Sameer Khan

Shift managers: 4

Kitchen team members: 16

Front-of-house team members: 14

Delivery team members: 8

Cleaning and stewarding staff: 6

Administrative and marketing staff: 5

**Total dummy active staff: 65** (6 leadership + 6 named operational leads + 4 shift managers + 16 kitchen + 14 front-of-house + 8 delivery + 6 cleaning/stewarding + 5 administration/marketing = 65). This is the canonical figure; do not use 58 anywhere it refers to the complete dummy staff set — that earlier figure was an arithmetic error and has been corrected.

### 4.3 System roles

Owner

General Manager

Operations Manager

Finance Manager

Kitchen Manager

Inventory Manager

Reservation Manager

Customer Support Agent

Marketing Manager

HR Manager

Shift Supervisor

Kitchen Staff

Front-of-House Staff

Delivery Coordinator

Read-Only Auditor

Each role will have backend-enforced permissions using the single canonical capability registry defined in `DATABASE_AND_API.md`. Navigation visibility is never the security boundary.

## 5. DUMMY CUSTOMER SEGMENTS

New customer: First recorded interaction or first order

Repeat customer: Two to four completed orders

Loyal customer: Five or more completed orders in 180 days

VIP customer: High-value or manually approved customer

At-risk customer: Previously active but no order in 45 days

Dormant customer: No order in 90 days

High average order value: Average direct order value above ₹1,200

Vegetarian preference

Vegan preference

Jain preference

Spice-sensitive customer

Family customer

Corporate customer

College group

Birthday and celebration customer

Delivery-first customer

Dine-in-first customer

Discount-sensitive customer

Complaint-recovery customer

## 6. DUMMY LEAD MODEL

### 6.1 Lead sources

Website enquiry

Phone enquiry

Walk-in enquiry

WhatsApp enquiry

Zomato lead or approved data import

Swiggy lead or approved data import

Meta campaign lead

Google campaign lead

Referral

Corporate outreach

Event or group booking enquiry

Offline flyer or QR campaign

### 6.2 Lead statuses

New

Contacted

Qualified

Interested

Follow-up Scheduled

Proposal Shared

Negotiating

Won

Lost

Closed

### 6.3 Dummy lead use cases

Corporate lunch order for 60 employees

Birthday party reservation for 25 guests

College event meal package for 120 guests

Recurring office snack delivery

Influencer collaboration

Bulk festival order

Catering enquiry

Restaurant franchise enquiry, marked out of scope and closed

## 7. DUMMY MENU CATALOGUE

All prices below are dummy Indian rupee values and are inclusive of assumed restaurant pricing before platform-specific charges. Final taxation, packaging, delivery, discounts, and aggregator pricing must be calculated through configured rules. All prices are stored as integer minor units (paise) in `BIGINT` columns ending in `_minor` — see `DATABASE_AND_API.md` §3.3.

### 7.1 Burgers

RKPR Classic Veg Burger — ₹179

Description: Crispy vegetable patty, lettuce, tomato, onion, pickles, and house burger sauce in a toasted sesame bun.

Food type: Vegetarian

Preparation time: 12 minutes

Calories: 540 kcal

Primary ingredients: Burger bun, vegetable patty, lettuce, tomato, onion, pickle, burger sauce

RKPR Spicy Paneer Burger — ₹229

Description: Grilled spicy paneer patty, jalapeños, onion, lettuce, chilli mayonnaise, and cheese.

Food type: Vegetarian

Preparation time: 14 minutes

Calories: 690 kcal

Smoky BBQ Chicken Burger — ₹259

Description: Grilled chicken patty, smoked barbecue sauce, caramelized onion, lettuce, tomato, and cheddar.

Food type: Non-vegetarian

Preparation time: 15 minutes

Calories: 720 kcal

Double Crunch Chicken Burger — ₹299

Description: Two crispy chicken fillets, cheese, pickles, coleslaw, and spicy house sauce.

Food type: Non-vegetarian

Preparation time: 17 minutes

Calories: 920 kcal

Jain Aloo Crunch Burger — ₹189

Description: Jain-style potato patty without onion or garlic, lettuce, tomato, and Jain mint sauce.

Food type: Jain vegetarian

Preparation time: 13 minutes

Calories: 510 kcal

### 7.2 Pizzas

Margherita Pizza, 8 inch — ₹219

Margherita Pizza, 11 inch — ₹349

Description: Tomato sauce, mozzarella, basil, and oregano.

Farmhouse Veg Pizza, 8 inch — ₹279

Farmhouse Veg Pizza, 11 inch — ₹429

Description: Onion, capsicum, mushroom, sweet corn, tomato, mozzarella, and herbs.

Paneer Tikka Pizza, 8 inch — ₹319

Paneer Tikka Pizza, 11 inch — ₹479

Description: Tandoori paneer, onion, capsicum, mozzarella, and mint drizzle.

BBQ Chicken Pizza, 8 inch — ₹349

BBQ Chicken Pizza, 11 inch — ₹529

Description: Barbecue chicken, onion, smoked sauce, mozzarella, and chilli flakes.

Mexican Fire Pizza, 8 inch — ₹329

Mexican Fire Pizza, 11 inch — ₹499

Description: Jalapeños, black beans, corn, peppers, salsa, cheese, and chipotle sauce.

### 7.3 Tacos

Crispy Veg Taco, two pieces — ₹199

Description: Crispy shells filled with seasoned vegetables, lettuce, salsa, cheese, and sour cream.

Paneer Chipotle Taco, two pieces — ₹239

Description: Grilled paneer, chipotle sauce, cabbage slaw, salsa, and cheese.

Chicken Salsa Taco, two pieces — ₹259

Description: Spiced chicken, salsa, lettuce, onion, cheese, and lime crema.

Loaded Bean Taco, two pieces — ₹219

Description: Black beans, corn, salsa, jalapeños, cheese, and sour cream.

### 7.4 Burritos and bowls

Veg Mexican Burrito — ₹249

Description: Mexican rice, beans, vegetables, salsa, cheese, lettuce, and sour cream.

Paneer Burrito — ₹289

Description: Paneer, Mexican rice, beans, grilled vegetables, salsa, cheese, and chipotle sauce.

Chicken Burrito — ₹319

Description: Grilled chicken, Mexican rice, beans, salsa, lettuce, cheese, and lime crema.

Veg Burrito Bowl — ₹269

Chicken Burrito Bowl — ₹339

### 7.5 Sides

Classic Fries — ₹109

Peri-Peri Fries — ₹129

Loaded Cheese Fries — ₹189

Chicken Loaded Fries — ₹239

Onion Rings — ₹149

Garlic Bread — ₹139

Cheese Garlic Bread — ₹179

Nachos with Salsa — ₹169

Loaded Veg Nachos — ₹229

Chicken Nuggets, six pieces — ₹199

Chicken Wings, six pieces — ₹269

### 7.6 Beverages

Classic Cola, 300 ml — ₹79

Lemon Soda — ₹99

Fresh Lime Water — ₹89

Iced Tea — ₹119

Cold Coffee — ₹159

Chocolate Shake — ₹179

Strawberry Shake — ₹179

Mango Shake — ₹179

Mineral Water, 500 ml — ₹40

### 7.7 Desserts

Chocolate Brownie — ₹159

Brownie with Vanilla Ice Cream — ₹219

Churros with Chocolate Dip — ₹189

New York Cheesecake Slice — ₹229

Soft Serve Cup — ₹99

### 7.8 Combos

Classic Veg Meal — ₹299

Includes: RKPR Classic Veg Burger, classic fries, and 300 ml cola.

Paneer Power Meal — ₹379

Includes: Spicy Paneer Burger, peri-peri fries, and iced tea.

Chicken Crunch Meal — ₹429

Includes: Double Crunch Chicken Burger, classic fries, and cola.

Pizza Sharing Combo — ₹699

Includes: One 11-inch Farmhouse Veg Pizza, garlic bread, two beverages, and one brownie.

Family Feast Veg — ₹1,249

Includes: Two 11-inch vegetarian pizzas, two veg burgers, two large fries, four beverages, and two desserts.

Family Feast Mixed — ₹1,499

Includes: One BBQ Chicken Pizza, one Farmhouse Pizza, two chicken burgers, two fries, four beverages, and two desserts.

### 7.9 Add-ons and modifiers

Cheese slice — ₹35

Extra paneer patty — ₹80

Extra chicken patty — ₹100

Extra vegetable patty — ₹60

Jalapeños — ₹25

Extra sauce — ₹20

Gluten-aware bun substitute — ₹60

Make it Jain — No charge where technically possible

Make it extra spicy — No charge

Remove ingredient — No charge

### 7.10 Menu availability rules

A product may become unavailable automatically only through an approved ingredient mapping rule and configured stock threshold.

Example: RKPR Classic Veg Burger becomes unavailable when burger buns or vegetable patties reach zero sellable stock.

Automatic unavailability must create an inventory and operations notification.

Manual override requires permission, reason, expiry time, and audit log.

## 8. DUMMY INVENTORY MASTER

### 8.1 Core inventory fields

Inventory item ID

Item name

Category

Storage zone

Unit of measurement

Current stock

Available stock

Reserved stock

Reorder level

Target stock

Maximum stock

Average unit cost

Preferred supplier

Alternative supplier

Lead time

Shelf life

Batch tracking requirement

Expiry tracking requirement

Allergen flags

Last counted time

Last received time

Stock status

### 8.2 Dummy stock catalogue

Burger buns — Unit: pieces — Current: 420 — Reorder: 120 — Target: 500 — Cost: ₹18 each — Supplier: Bengaluru Bakers Supply — Shelf life: 4 days

Gluten-aware buns — Unit: pieces — Current: 35 — Reorder: 10 — Target: 40 — Cost: ₹42 each — Supplier: GreenGrain Foods — Shelf life: 5 days

Vegetable burger patties — Unit: pieces — Current: 210 — Reorder: 60 — Target: 250 — Cost: ₹34 each — Supplier: FreshForm Foods — Frozen shelf life: 60 days

Paneer burger patties — Unit: pieces — Current: 120 — Reorder: 40 — Target: 150 — Cost: ₹58 each — Supplier: Nandi Dairy Foods — Chilled shelf life: 7 days

Chicken burger patties — Unit: pieces — Current: 180 — Reorder: 50 — Target: 220 — Cost: ₹72 each — Supplier: Southern Poultry Co. — Frozen shelf life: 45 days

Crispy chicken fillets — Unit: pieces — Current: 160 — Reorder: 45 — Target: 200 — Cost: ₹78 each — Supplier: Southern Poultry Co.

Pizza dough balls, small — Unit: pieces — Current: 130 — Reorder: 40 — Target: 170 — Cost: ₹24 each — Supplier: In-house production

Pizza dough balls, large — Unit: pieces — Current: 95 — Reorder: 30 — Target: 130 — Cost: ₹38 each — Supplier: In-house production

Mozzarella cheese — Unit: kilograms — Current: 38.5 kg — Reorder: 12 kg — Target: 45 kg — Cost: ₹540 per kg — Supplier: Nandi Dairy Foods

Cheddar slices — Unit: slices — Current: 390 — Reorder: 120 — Target: 500 — Cost: ₹16 each — Supplier: Nandi Dairy Foods

Paneer — Unit: kilograms — Current: 29 kg — Reorder: 8 kg — Target: 35 kg — Cost: ₹390 per kg — Supplier: Nandi Dairy Foods

Boneless chicken — Unit: kilograms — Current: 34 kg — Reorder: 10 kg — Target: 42 kg — Cost: ₹310 per kg — Supplier: Southern Poultry Co.

French fries, frozen — Unit: kilograms — Current: 62 kg — Reorder: 18 kg — Target: 75 kg — Cost: ₹155 per kg — Supplier: FrostBite Distributors

Onion rings, frozen — Unit: kilograms — Current: 14 kg — Reorder: 5 kg — Target: 18 kg — Cost: ₹220 per kg — Supplier: FrostBite Distributors

Taco shells — Unit: pieces — Current: 360 — Reorder: 100 — Target: 450 — Cost: ₹12 each — Supplier: MexiSource India

Large tortillas — Unit: pieces — Current: 240 — Reorder: 70 — Target: 300 — Cost: ₹17 each — Supplier: MexiSource India

Mexican rice — Unit: kilograms — Current: 28 kg — Reorder: 8 kg — Target: 35 kg — Cost: ₹92 per kg — Supplier: Metro Grain Traders

Black beans — Unit: kilograms — Current: 18 kg — Reorder: 5 kg — Target: 22 kg — Cost: ₹145 per kg — Supplier: Metro Grain Traders

Lettuce — Unit: kilograms — Current: 17 kg — Reorder: 5 kg — Target: 22 kg — Cost: ₹105 per kg — Supplier: GreenLeaf Produce

Tomatoes — Unit: kilograms — Current: 24 kg — Reorder: 7 kg — Target: 30 kg — Cost: ₹42 per kg — Supplier: GreenLeaf Produce

Onions — Unit: kilograms — Current: 30 kg — Reorder: 8 kg — Target: 38 kg — Cost: ₹38 per kg — Supplier: GreenLeaf Produce

Capsicum — Unit: kilograms — Current: 12 kg — Reorder: 4 kg — Target: 16 kg — Cost: ₹84 per kg — Supplier: GreenLeaf Produce

Mushrooms — Unit: kilograms — Current: 8 kg — Reorder: 3 kg — Target: 10 kg — Cost: ₹190 per kg — Supplier: GreenLeaf Produce

Sweet corn — Unit: kilograms — Current: 15 kg — Reorder: 4 kg — Target: 18 kg — Cost: ₹120 per kg — Supplier: FrostBite Distributors

Jalapeños — Unit: kilograms — Current: 7 kg — Reorder: 2 kg — Target: 9 kg — Cost: ₹280 per kg — Supplier: MexiSource India

Pickles — Unit: kilograms — Current: 10 kg — Reorder: 3 kg — Target: 12 kg — Cost: ₹160 per kg — Supplier: TasteCraft Condiments

Burger sauce — Unit: litres — Current: 18 L — Reorder: 5 L — Target: 22 L — Cost: ₹210 per litre — Supplier: In-house production

Chipotle sauce — Unit: litres — Current: 12 L — Reorder: 4 L — Target: 15 L — Cost: ₹260 per litre — Supplier: TasteCraft Condiments

Barbecue sauce — Unit: litres — Current: 11 L — Reorder: 3 L — Target: 14 L — Cost: ₹230 per litre — Supplier: TasteCraft Condiments

Tomato pizza sauce — Unit: litres — Current: 21 L — Reorder: 6 L — Target: 26 L — Cost: ₹175 per litre — Supplier: In-house production

Cooking oil — Unit: litres — Current: 95 L — Reorder: 25 L — Target: 120 L — Cost: ₹128 per litre — Supplier: Metro Oil Traders

Cola syrup — Unit: litres — Current: 20 L — Reorder: 6 L — Target: 25 L — Cost: ₹145 per litre — Supplier: Beverage Partner Demo

Mineral water bottles — Unit: bottles — Current: 420 — Reorder: 120 — Target: 500 — Cost: ₹16 each — Supplier: ClearSpring Beverages

Brownies — Unit: pieces — Current: 80 — Reorder: 25 — Target: 100 — Cost: ₹62 each — Supplier: Bengaluru Bakers Supply

Cheesecake slices — Unit: pieces — Current: 42 — Reorder: 12 — Target: 50 — Cost: ₹98 each — Supplier: SweetLine Desserts

Vanilla ice cream — Unit: litres — Current: 16 L — Reorder: 5 L — Target: 20 L — Cost: ₹240 per litre — Supplier: Nandi Dairy Foods

Paper burger boxes — Unit: pieces — Current: 900 — Reorder: 250 — Target: 1,200 — Cost: ₹7 each — Supplier: EcoPack Bengaluru

Pizza boxes, small — Unit: pieces — Current: 320 — Reorder: 100 — Target: 400 — Cost: ₹11 each — Supplier: EcoPack Bengaluru

Pizza boxes, large — Unit: pieces — Current: 270 — Reorder: 80 — Target: 350 — Cost: ₹16 each — Supplier: EcoPack Bengaluru

Takeaway bags — Unit: pieces — Current: 540 — Reorder: 150 — Target: 700 — Cost: ₹8 each — Supplier: EcoPack Bengaluru

Napkin packs — Unit: packs — Current: 310 — Reorder: 80 — Target: 400 — Cost: ₹12 per pack — Supplier: EcoPack Bengaluru

### 8.3 Inventory states

In stock

Low stock

Critical stock

Out of stock

Reserved

Quarantined

Expired

Damaged

Under count review

Discontinued

### 8.4 Stock movement types

Purchase receipt

Kitchen issue

Direct consumption

Recipe consumption

Manual adjustment

Waste

Damage

Expiry

Return to supplier

Transfer between storage zones

Cycle count correction

Opening balance

Reservation or event allocation

Order reservation

Order release

## 9. DUMMY SUPPLIER DIRECTORY

### Bengaluru Bakers Supply

Supplier code: SUP-BAK-001

Contact person: Harish Verma

Phone: +91 98860 11001

Email: orders@bengaluru-bakers-demo.example

Address: 41, Industrial Bakery Lane, Peenya, Bengaluru 560058

Supply categories: Burger buns, brownies, garlic bread

Normal lead time: 1 day

Payment terms: 15 days

Minimum order value: ₹5,000

### Nandi Dairy Foods

Supplier code: SUP-DAI-002

Contact person: Divya Rao

Phone: +91 98860 11002

Email: sales@nandi-dairy-demo.example

Address: 12, Dairy Market Road, Yeshwanthpur, Bengaluru 560022

Supply categories: Mozzarella, cheddar, paneer, ice cream

Normal lead time: 1 day

Payment terms: 15 days

Minimum order value: ₹7,500

### Southern Poultry Co.

Supplier code: SUP-POU-003

Contact person: Imran Ali

Phone: +91 98860 11003

Email: dispatch@southern-poultry-demo.example

Address: 27, Cold Chain Park, Nelamangala, Bengaluru Rural 562123

Supply categories: Chicken patties, chicken fillets, boneless chicken

Normal lead time: 2 days

Payment terms: 7 days

Minimum order value: ₹10,000

### GreenLeaf Produce

Supplier code: SUP-VEG-004

Contact person: Lakshmi Narayan

Phone: +91 98860 11004

Email: supply@greenleaf-produce-demo.example

Address: Stall 118, APMC Yard, Yeshwanthpur, Bengaluru 560022

Supply categories: Lettuce, tomato, onion, capsicum, mushroom, herbs

Normal lead time: Same day or next morning

Payment terms: Weekly settlement

Minimum order value: ₹2,000

### FrostBite Distributors

Supplier code: SUP-FRO-005

Contact person: Akash Mehta

Phone: +91 98860 11005

Email: orders@frostbite-demo.example

Address: Unit 8, Cold Storage Estate, Hoskote, Bengaluru Rural 562114

Supply categories: Fries, onion rings, corn, frozen products

Normal lead time: 2 days

Payment terms: 15 days

Minimum order value: ₹8,000

### MexiSource India

Supplier code: SUP-MEX-006

Contact person: Maria D'Souza

Phone: +91 98860 11006

Email: sales@mexisource-demo.example

Address: 63, Food Import Hub, Whitefield, Bengaluru 560066

Supply categories: Taco shells, tortillas, jalapeños, Mexican ingredients

Normal lead time: 3 days

Payment terms: Advance for imported items

Minimum order value: ₹12,000

### TasteCraft Condiments

Supplier code: SUP-CON-007

Contact person: Rohit Bansal

Phone: +91 98860 11007

Email: b2b@tastecraft-demo.example

Address: 14, Food Processing Cluster, Bommasandra, Bengaluru 560099

Supply categories: Sauces, pickles, condiments

Normal lead time: 3 days

Payment terms: 15 days

Minimum order value: ₹6,000

### EcoPack Bengaluru

Supplier code: SUP-PAC-008

Contact person: Asha Menon

Phone: +91 98860 11008

Email: orders@ecopack-demo.example

Address: 77, Packaging Industrial Area, Kumbalgodu, Bengaluru 560074

Supply categories: Boxes, bags, napkins, cups, cutlery

Normal lead time: 4 days

Payment terms: 30 days

Minimum order value: ₹15,000

## 10. ORDER WORKFLOW

### 10.1 Order sources

Direct website

Restaurant mobile web ordering

WhatsApp-assisted order

Phone-assisted order

Walk-in order imported from POS where supported

Zomato approved integration or import

Swiggy approved integration or import

Corporate bulk order

Event order

### 10.2 Online order statuses

Draft

Pending Payment

Payment Verification Pending

Confirmed

Accepted

Preparing

Quality Check

Ready

Picked Up

Out for Delivery

Delivered

Cancelled

Refund Requested

Refund Processing

Refunded

Failed

### 10.3 Order business rules

Authoritative price, discount, tax, packaging, and total calculations happen on the backend.

Client-provided prices are ignored.

Status transitions follow explicit rules.

Every status change stores actor, timestamp, reason where needed, and source.

Cancellation and refund actions require permission.

Inventory is reserved only after the configured confirmation point.

Inventory consumption occurs at the configured preparation or fulfilment event.

Cancelled orders release unconsumed reserved stock.

Duplicate payment or webhook events must not create duplicate orders or refunds.

## 11. RESERVATION WORKFLOW

### 11.1 Reservation states

Requested

Pending Review

Needs Clarification

Approved

Rejected

Confirmation Sending

Confirmed

Reminder Scheduled

Arrived

Seated

Completed

No Show

Cancelled by Customer

Cancelled by Restaurant

### 11.2 Reservation rules

Every reservation requires human approval.

No automated approval is permitted in the initial system.

Approval checks capacity, time, seating zone, special requests, operating hours, and conflicts.

WhatsApp or email confirmation is sent only after approval.

A new reservation request creates an operational notification.

A reminder is scheduled according to configured rules.

Large groups may require deposit or manual owner approval.

Groups above 18 guests are handled as event or bulk leads.

## 12. LOYALTY PROGRAM

Program name: RKPR Rewards

Enrollment: Customer consent required

Base earning rule: 1 point for every ₹10 of eligible direct spend

Welcome bonus: 100 points after first completed direct order

Birthday bonus: 200 points once per year when verified and consented

Referral bonus: 150 points after referred customer's first completed direct order

Redemption threshold: Minimum 300 points

Redemption value: 100 points equals ₹25

Maximum redemption: 20 percent of eligible order subtotal

Points expiry: 365 days after earning

Excluded spend: Taxes, delivery fees, refunded amounts, excluded campaigns, aggregator orders unless explicitly configured

Loyalty adjustments require reason and audit log.

## 13. MARKETING AND CONSENT MODEL

Consent types:

WhatsApp marketing consent

Email marketing consent

SMS marketing consent

Loyalty consent

Feedback request consent

Personalization consent

Consent records store source, text or version, timestamp, status, withdrawal timestamp, and evidence where applicable.

Campaign examples:

First-order offer

Dormant customer win-back

Birthday reward

Weekend family combo

Vegetarian customer campaign

Corporate lunch campaign

High-value customer appreciation

New pizza launch

Feedback recovery campaign

Campaigns must respect consent, suppression lists, frequency caps, quiet hours, audience rules, and communication provider policies.

## 14. KEY BUSINESS METRICS

Daily revenue

Order count

Average order value

Direct versus aggregator revenue

Completed versus cancelled orders

Preparation time

Delivery time

Refund rate

Lead response time

Lead conversion rate

Reservation approval rate

Reservation no-show rate

Customer repeat rate

Customer lifetime value

Loyalty enrollment and redemption

Campaign delivery, engagement, and conversion

Complaint rate

Feedback score

Inventory value

Waste value

Stock-out events

Supplier lead-time reliability

Staff attendance and shift coverage

## 15. COMPLETE IMPLEMENTATION PHASES

The project must be built phase by phase, in the exact sequence and using the exact names defined in `/ROADMAP.md` (Phase 0 through Phase 19). Claude must not proceed to the next phase until the current phase's completion criteria are met, verified, and documented. Later phases may refine earlier code, but must not invalidate settled architecture or security rules.

# PHASE 0 — PROJECT RULES AND DOCUMENTATION LOCK

## Objective

Perform a full documentation, architecture, repository, and implementation-readiness audit before any code is written, and repair any contradiction found across the canonical documents.

## Scope

- Read every authoritative document fully
- Confirm module boundaries, canonical dummy data, and the single-business/non-multi-tenant architecture
- Confirm the RAG/embeddings/vector-search/pgvector, n8n, and Temporal exclusions
- Confirm the approved frontend, backend, database, infrastructure, deployment, and testing stack
- Resolve any contradiction found between documents (see `CLAUDE.md` §1.1 for the authority order used to resolve conflicts)
- Produce a documentation-repair report

## Definition of Done

- All twelve canonical documents exist as Markdown at their required repository paths and are internally consistent
- There is exactly one phase sequence (this one) and no document references a conflicting one
- No open contradiction remains between documents

# PHASE 1 — REPOSITORY AND DEVELOPMENT FOUNDATION

## Objective

Create the production-grade project foundation and eliminate architectural ambiguity before feature development begins.

## Scope

- Monorepo structure (`apps/dashboard`, `apps/api`, `apps/worker`, `packages/ui`, `packages/contracts`, `packages/api-client`, `packages/config`)
- Next.js dashboard application shell
- FastAPI backend application shell
- Background worker application shell (ARQ)
- Environment validation
- Linting, formatting, strict typing, testing, and CI baseline
- Structured logging, request IDs, health endpoints, and Sentry placeholders
- Initial design system and responsive application shell
- Docker is intentionally deferred to a later deployment/environment-hardening roadmap item — its absence here is expected, not a defect

## Backend tasks

- FastAPI app factory
- Configuration management (Pydantic settings)
- Database session and pooling scaffolding
- Authentication dependency placeholders
- Error handling conventions
- Pagination contracts
- Health and readiness endpoints
- Structured logs and correlation IDs
- Worker (ARQ) framework and scheduler baseline

## Frontend tasks

- Next.js application shell
- TypeScript strict mode
- Tailwind and component foundation
- Navigation layout for all twelve sections
- Permission-aware route placeholders without frontend-only security assumptions
- Global loading and error boundaries
- Server-state provider (TanStack Query)
- Accessibility baseline

## Security tasks

- Secret separation
- CORS configuration by environment
- Secure header baseline
- No service-role credentials in browser
- Environment schema validation
- Initial rate-limit framework

## Performance tasks

- Route-level code splitting
- Bounded API defaults
- Database connection pooling
- No unbounded list patterns
- Query logging in development
- Initial bundle and build review

## Definition of Done

- All applications start locally
- Production builds succeed
- Format, lint, type-check, unit-test, and CI commands pass
- Health endpoints work without leaking secrets
- No real credentials are committed
- Repository documentation matches the actual setup

# PHASE 2 — DATABASE FOUNDATION AND MIGRATIONS

## Objective

Establish the authoritative PostgreSQL schema foundation and migration framework before any business module is built.

## Scope

- Configure Supabase PostgreSQL
- Establish the Alembic migration framework
- Create extension and schema baseline
- Add a system configuration table where justified
- Add the audit-event foundation
- Add the outbox/event foundation
- Define UTC timestamp conventions and the `Asia/Kolkata` display-timezone convention
- Define the identifier strategy (UUID primary keys, human-readable references such as `order_number`, `lead_number`)
- Implement initial SQLAlchemy base models and session management
- Add canonical development seed-data scaffolding (including the corrected 65-person dummy staff set, to be populated fully in later phases as each module's schema lands)

## Definition of Done

- Clean database migration succeeds
- Migration succeeds from the latest previous schema state
- Constraints, indexes, and identifier conventions are documented and enforced
- No destructive migration ships without a reviewed strategy

# PHASE 3 — AUTHENTICATION, USERS, ROLES, AND PERMISSIONS

## Objective

Implement secure staff access and backend-enforced authorization before business modules are created.

## Scope

- Supabase Auth integration
- Login, logout, refresh, reset, invitation, and session flows
- Staff user profile
- The single canonical capability registry (dot-separated permission codes) and role/permission model
- Department and record-scope rules
- Owner and privileged account MFA readiness
- Session visibility and revocation where supported
- Authentication and security audit events

## Database tasks

- Staff users
- Roles
- Permissions (canonical capability registry)
- Role-permission mappings
- Staff-role assignments
- Departments
- Sessions or session metadata where appropriate
- Invitation records
- Security event audit records

## Backend tasks

- Token validation
- Current-user endpoint
- Centralized authorization service
- Permission decorators or dependencies
- Invitation workflow
- Account status enforcement
- Brute-force and abuse protection
- Audit logging for security-sensitive actions

## Frontend tasks

- Login page
- Password reset flows
- Invitation acceptance
- Account security page
- Session or device management if supported
- Permission-aware navigation
- Forbidden and expired-session states

## Definition of Done

- Protected routes reject unauthenticated access
- Backend rejects unauthorized actions even when requests are manually constructed
- Role changes are audited
- Account disabling blocks access
- Security and permission tests pass

# PHASE 4 — DASHBOARD SHELL AND SHARED UI SYSTEM

## Objective

Build the responsive, high-speed dashboard framework and shared UI system that later modules will populate with real data, without hardcoded production data.

## Scope

- Owner, general manager, operations, kitchen, reservation, and marketing dashboard shells
- Role-specific widget placeholders
- Date-range controls
- Operational activity timeline
- Alerts and notification preview
- Shared design-system components in `packages/ui`: tables, filters, forms, dialogs, charts, skeletons, badges, pagination controls
- Permission-aware UI behavior

## Initial dummy widgets (development-only reference values)

Revenue today: ₹84,620

Orders today: 216

Average order value: ₹392

Active leads: 38

Reservations today: 17

Low-stock items: 9

Orders preparing: 14

Pending reservation approvals: 5

Customer feedback average: 4.4 out of 5

These values are seed or demonstration data only and must be replaced by API-driven aggregates as each contributing module ships.

## Backend tasks

- Aggregation endpoints
- Role-scoped metrics
- Date-range validation
- Cached aggregate strategy where justified
- Bounded activity feed

## Frontend tasks

- KPI cards
- Charts (Apache ECharts)
- Operational tables (TanStack Table)
- Skeleton loading
- Empty and degraded states
- Date filters
- Responsive widget layout

## Definition of Done

- Dashboard uses real API contracts
- No hardcoded production metrics remain
- Role-scoped dashboards respect permissions
- Date filters and loading states work
- Slow or failed widgets do not block the entire page

# PHASE 5 — CUSTOMER AND LEAD CRM

## Objective

Create a complete customer lifetime record and a full lead-to-conversion pipeline that supports service, personalization, retention, safe segmentation, and sales tracking.

## Scope — Customers

- Customer list and search
- Customer profile
- Contact details, addresses, preferences, dietary needs
- Order history, reservation history, communication history
- Feedback and complaints
- Loyalty account
- Tags and segments
- Notes
- Timeline
- Duplicate detection and merge
- Consent and suppression status
- Soft deletion and restoration

## Scope — Leads

- Lead list
- Lead profile
- Source tracking
- Status pipeline
- Assignment
- Follow-up scheduling
- Notes and activities
- Proposal or quote references
- Loss reasons
- Conversion to customer
- Corporate and event enquiries
- Campaign attribution

## Dummy customer examples

Ananya Rao — Vegetarian — 12 completed orders — Favorite item: Paneer Tikka Pizza — Loyalty balance: 680 points

Rahul Mehta — Non-vegetarian — 8 completed orders — Favorite item: Double Crunch Chicken Burger — At-risk

Shreya Kulkarni — Jain preference — 5 completed orders — Favorite item: Jain Aloo Crunch Burger

BrightWave Technologies — Corporate customer — Monthly lunch orders — Assigned account owner: Nikhil Jain

## Dummy lead records

LEAD-0001 — BrightWave Technologies — Corporate lunch for 60 staff — Budget ₹18,000 — Source: Website — Status: Qualified

LEAD-0002 — Priya Birthday Event — 25 guests — Budget ₹22,000 — Source: WhatsApp — Status: Follow-up Scheduled

LEAD-0003 — EastPoint College Fest — 120 meal boxes — Budget ₹48,000 — Source: Referral — Status: Negotiating

## Lead workflow

New → Contacted → Qualified → Interested → Follow-up Scheduled → Proposal Shared → Negotiating → Won or Lost → Closed

## Backend tasks

- Customer CRUD with permission checks
- Server-side pagination, search, filtering, and sorting
- Customer timeline service
- Duplicate detection
- Safe merge transaction
- Consent management
- Segment calculation hooks
- Lead CRUD, assignment, and activity history
- Follow-up jobs and reminders
- Lead-source normalization
- Conversion transaction
- Duplicate customer reconciliation

## Frontend tasks

- Virtualized or bounded customer table
- Customer detail tabs
- Timeline
- Merge review UI
- Consent panel
- Tags and notes
- Export request flow
- Lead pipeline and table views
- Lead detail, assignment controls, follow-up calendar
- Conversion review
- Loss-reason capture

## Definition of Done

- Large customer and lead lists never load fully
- Duplicate merge preserves histories
- Sensitive actions are audited
- Customer deletion is soft by default
- Customer and lead access follows role and record scope
- Conversion preserves full lead history
- Won leads create or link to customers safely
- Follow-up reminders are durable background jobs

# PHASE 6 — MENU AND PRODUCT MANAGEMENT

## Objective

Create controlled menu and product operations with recipe-based costing and channel-aware availability.

## Scope

- Menu categories, products, and variants
- Modifiers and add-ons, combos
- Prices and availability
- Recipe and ingredient mapping (recipe definitions; live stock deduction lands in Phase 7/8 once orders and inventory exist)
- Product images, allergens, and nutrition
- Costing, margins, and pricing visibility rules
- Canonical RKPR menu and prices (§7 of this document)

## Seed data

Use the menu dummy data in §7 of this document for development and test seeding.

## Backend tasks

- Menu category, product, and variant models
- Modifier group and modifier models
- Recipe mapping (definition only at this phase)
- Product availability source tracking (manual, inventory-derived, schedule, integration, override)

## Frontend tasks

- Menu manager
- Product editor
- Recipe builder
- Availability override controls

## Definition of Done

- Seed data matches this document exactly
- Prices and variants are data-driven, never hardcoded in the UI
- Recipe versions are preserved
- Availability state has an explainable source

# PHASE 7 — ORDERS AND RESTAURANT OPERATIONS

## Objective

Create complete online order visibility and operational status handling without duplicating unsupported offline POS fulfilment.

## Scope

- Dine-in, takeaway, delivery, online, WhatsApp-assisted, phone-assisted, corporate, and event ordering foundations
- Order state machine (§10.2 of this document)
- Order items, modifiers, and price breakdown
- Kitchen and preparation workflow
- Taxes, discounts, payments, refunds, cancellations, and status/audit history
- Realtime operational updates
- Inventory reservation and consumption hooks (activated once Phase 8 lands; this phase implements the hook points and contracts)

## Backend tasks

- Order creation and import contracts
- Backend total calculation (authoritative; client totals are ignored)
- Status-transition service
- Inventory reservation hooks
- Payment event idempotency
- Refund request workflow
- Late-order alerts
- Outbox-based communication events where required

## Frontend tasks

- Order queue
- Kitchen-oriented board
- Order detail
- Status controls
- Timer indicators
- Filters by source, status, date, and assignee
- Refund and cancellation review

## Definition of Done

- Invalid status transitions are rejected
- Duplicate webhook events do not duplicate orders or payments
- Order pages remain responsive with large history
- Every sensitive override is audited
- Offline POS workflow is not falsely duplicated

# PHASE 8 — INVENTORY AND SUPPLIER MANAGEMENT

## Objective

Create controlled stock operations with recipe-based deduction and complete stock history, and connect them to the order and menu-availability hooks established in Phases 6 and 7.

## Scope

- Ingredients, units, batches, expiry, FIFO/FEFO guidance, movements, waste, and cycle counts
- Recipe-based deductions activated against live orders
- Storage zones
- Suppliers, purchase orders, receiving, valuation, alerts, and vendor performance
- Reorder alerts
- Product availability automation (menu items become unavailable when mapped ingredients are exhausted)

## Seed data

Use the inventory and supplier dummy data in §8 and §9 of this document for development and test seeding.

## Backend tasks

- Inventory item and batch models
- Stock ledger (append-only movements)
- Transaction-safe reservation and consumption
- Reorder calculations
- Expiry and batch handling
- Purchase receipt workflow
- Controlled menu unavailability triggers

## Frontend tasks

- Inventory table
- Stock movement forms
- Purchase receipt screen
- Supplier profiles
- Low-stock and expiry dashboards

## Definition of Done

- Stock ledger is auditable
- Inventory changes are transaction-safe
- Product availability rules work without silent changes
- Manual overrides require reason and permission
- Large stock history uses pagination and indexed filters
- Seed data matches §8/§9 of this document exactly

# PHASE 9 — RESERVATIONS AND CALENDAR

## Objective

Implement human-approved reservations with capacity control, notifications, reminders, and attendance status.

## Scope

- Reservation request intake
- Human approval queue (no automated approval)
- Calendar and timeline views (day/week/month/agenda)
- Table and seating-zone assignment
- Guest count and special requests
- Conflict and capacity checks
- Confirmation messaging
- Reminders
- Arrival, seating, completion, cancellation, and no-show states
- Group and event reservations, including conversion to a lead for groups above 18 guests

## Backend tasks

- Reservation state machine (§11.1 of this document)
- Capacity checking
- Approval and rejection actions
- Reminder scheduling
- Notification events
- Calendar adapter
- Large-group conversion to lead

## Frontend tasks

- Approval inbox
- Calendar
- Reservation detail
- Capacity view
- Table assignment
- Conflict warnings
- Arrival and seating actions

## Definition of Done

- No reservation is automatically approved
- Confirmation sends only after approval
- Conflicts are detected
- New requests create operational notifications
- Reminder jobs survive browser closure

# PHASE 10 — COMMUNICATION HUB AND OPERATIONAL TASKS

## Objective

Unify customer conversations and outbound communication while maintaining consent, assignment, delivery status, and complete history, and coordinate cross-module operational work through the Tasks system.

## Scope

- WhatsApp conversations, email conversations, SMS records, website enquiries, phone call notes
- Assigned staff and conversation statuses
- Templates and attachments
- Delivery and failure statuses
- Search and filters
- Customer and lead linking
- Operational tasks: creation sources, assignment, priority, due time, completion evidence, recurring tasks
- Notifications center

## Backend tasks

- Conversation and message models
- Channel adapters
- Webhook processing and signature validation
- Message deduplication
- Delivery receipt handling
- Assignment and unread counts
- Template controls
- Consent enforcement
- Task models, assignment, and recurrence
- Notification deduplication and delivery

## Frontend tasks

- Inbox
- Conversation detail
- Composer
- Channel status
- Assignment
- Internal notes
- Attachment preview
- Search and pagination
- Task lists (my tasks, team tasks, due today, overdue, blocked)
- Notification center

## Definition of Done

- Messages are deduplicated
- Permissions apply to conversation records and attachments
- Failed delivery is visible
- Human staff work directly in conversations; no separate handoff module is created
- Every task has a clear owner or queue and validated status transitions
- Notifications are deduplicated and link to the correct record

# PHASE 11 — KNOWLEDGE BASE AND STAFF OPERATIONS

## Objective

Create a secure internal document repository without RAG, embeddings, or semantic vector search, and manage staff profiles, departments, schedules, leave, training, and HR-sensitive data with strict permission separation.

## Scope — Knowledge Base

- Folders, documents, metadata, permissions, versions
- Upload scanning, preview, download
- Keyword or PostgreSQL full-text search
- Archive and restoration

## Scope — Staff & HR

- Staff profiles, departments, roles
- Employment status and system access status (kept separate)
- Contact and emergency details, joining date and documents
- Shift assignments and scheduling
- Attendance summary, leave requests
- Training and certification
- Performance notes
- Disciplinary records with strict permissions
- Staff activity and audit visibility
- The canonical dummy staff set of 65 active staff (§4 of this document)

## Dummy document categories

Kitchen SOPs

Cleaning checklists

Opening and closing procedures

Food safety procedures

Supplier contacts

Employee handbook

Reservation handling guide

Complaint resolution guide

Marketing guidelines

Emergency contacts

## Backend tasks

- Knowledge folder/document/version models with PostgreSQL full-text search
- Staff HR models
- Permission separation for sensitive HR data
- Leave workflow
- Training expiry reminders
- Document security
- Shift data interfaces

## Frontend tasks

- Knowledge Base browser and editor
- Staff directory
- Staff profile
- Leave review
- Training tracker
- Shift overview
- Restricted HR panels

## Definition of Done

- Files are private by default; signed URLs are permission checked
- Upload validation and malware scanning pipeline exist
- Search is bounded, indexed, and never uses RAG or vector search
- HR-sensitive fields are strictly permissioned
- Staff self-access and manager access follow scope rules
- Sensitive changes are audited
- Seed staff data uses the canonical 65-person set

# PHASE 12 — LOYALTY, OFFERS, AND CAMPAIGNS

## Objective

Build the loyalty ledger, offers/coupons engine, customer segmentation, and consent-aware marketing campaigns.

## Scope

- Loyalty accounts and immutable point ledger (§12 of this document)
- Rewards, offers, coupons, eligibility, and redemption
- Customer segments and audience management
- Campaigns through connected channels (WhatsApp, email, SMS)
- Consent and suppression, frequency caps
- Audience preview, scheduled sending, delivery analytics
- Campaign attribution

## Backend tasks

- Loyalty ledger (append-only) and earning/redemption rules
- Offer and coupon models with deterministic promotion evaluation order
- Audience query builder using approved fixed business logic, not a generic workflow builder
- Campaign jobs, frequency caps, suppression enforcement

## Frontend tasks

- Loyalty settings and customer loyalty profile
- Offer and coupon management
- Campaign list and detail, audience preview
- Segment builder

## Definition of Done

- Consent is enforced at send time
- Loyalty balance uses an auditable, append-only ledger
- Duplicate reward issuance is prevented
- Campaign sending occurs in background jobs (ARQ)
- Promotion evaluation is deterministic and matches order-total calculation exactly

# PHASE 13 — FEEDBACK, COMPLAINTS, AND SERVICE RECOVERY

## Objective

Build feedback collection, the complaint lifecycle, and accountable service-recovery workflows.

## Scope

- Feedback requests and reviews, rating dimensions
- Complaint lifecycle: category, severity, status, assignment, SLA
- Escalation and root-cause tracking
- Compensation approval routed through the correct order/loyalty/promotion module (never directly mutated from the complaint screen)
- Resolution and follow-up
- Customer recovery history and the `complaint_recovery` segment

## Backend tasks

- Feedback ingestion and idempotent request scheduling
- Complaint workflow, SLA tracking, escalation rules
- Recovery credit controls routed through authorized workflows

## Frontend tasks

- Feedback dashboard
- Complaint queue and detail
- Recovery action panel

## Definition of Done

- Complaints have assignment, status, SLA, and history
- Compensation requires correct approval and uses the correct module
- Root-cause history is preserved
- Reports use meaningful denominators (for example, complaint rate against relevant sales, not raw counts)

# PHASE 14 — REPORTS, ANALYTICS, AND CONTROLLED AI

## Objective

Create trustworthy management reporting, scheduled summaries, attractive visual analytics, and controlled AI assistance.

## Scope

- Daily, weekly, and monthly reports
- Revenue, order, customer, lead, reservation, inventory, waste, marketing, and staff analytics
- Export generation
- Owner email delivery with configurable recipients
- AI summaries and anomaly explanations (advisory only)

## Dummy report recipients

Primary owner recipient: owner@rkpr-demo.example

Secondary manager recipient: manager@rkpr-demo.example

Finance recipient: finance@rkpr-demo.example

These are dummy values and must be configurable in Settings, never hardcoded.

## Backend tasks

- Aggregation queries and centrally-defined metric formulas
- Report definitions and background PDF/spreadsheet generation (openpyxl for XLSX, Playwright/Chromium for PDF)
- Secure expiring downloads
- Scheduled delivery with failure retries
- AI provider abstraction (OpenAI primary, Groq optional fallback) with structured outputs, permission scoping, and cost controls — implemented and credentialed only in this phase, not earlier

## Frontend tasks

- Reports library
- Date and comparison filters
- Charts (Apache ECharts)
- Export request status
- Scheduled report configuration
- AI summary panel with explicit limitations clearly labeled as AI-generated

## Definition of Done

- Reports use authoritative database data
- Heavy reports do not block API requests
- Report recipients are configurable
- AI cannot bypass permissions or perform sensitive actions without confirmation
- Zero-denominator metrics do not produce misleading percentages

# PHASE 15 — INTEGRATIONS, AUTOMATIONS, JOBS, AND REALTIME

## Objective

Connect approved external services, centralize restaurant-specific configuration, and complete cross-module operational automation and realtime behavior — without creating a generic customization platform or a generic workflow builder.

## Scope

- Restaurant profile, operating hours, contact details, tax and charge settings (Settings)
- Report recipients and notification settings
- WhatsApp, email, SMS, calendar, website, POS, Zomato, and Swiggy integrations or approved imports where supported
- Webhook administration and signature verification
- Transactional outbox
- Worker queues and scheduler (ARQ)
- Retries and dead-letter recovery
- Controlled backend automations (the approved automation catalog from `INTEGRATIONS_AUTOMATIONS_REALTIME.md` §14)
- Authenticated, scoped realtime channels (orders, reservations, conversations, notifications, critical inventory alerts)
- Integration health and reconciliation
- Audit-log viewer and system monitoring

## Backend tasks

- Integration adapters and credential references
- Signature validation and connection testing
- Sync metadata and reconciliation jobs
- Settings validation and audit logs
- Domain event and outbox publication
- Scheduled jobs (reminders, expiry checks, reconciliation)

## Frontend tasks

- Settings pages
- Integration cards with connected/disconnected/degraded/error states
- Audit log search
- System health summary

## Definition of Done

- No fake integration is displayed as connected
- Credentials remain server-side
- Webhooks are verified and deduplicated
- Core dashboard works when optional integrations are disconnected
- Automations run without a browser session; duplicate execution does not duplicate business effects
- Realtime failures recover through API reconciliation

# PHASE 16 — SECURITY, PERFORMANCE, AND QUALITY HARDENING

## Objective

Harden the complete system for production without compromising security, performance, data integrity, or operational reliability.

## Scope

- Complete permission review across every role
- Security hardening (auth abuse, IDOR, injection, XSS, CSRF, SSRF, file/webhook security)
- Query and index review
- Performance and load testing (k6)
- Accessibility and UX quality review
- Observability, alerting, backups, and restore-test validation
- Incident-response readiness

## Required checks

- Clean-database migration and upgrade-from-previous-state validation
- Production frontend build and backend/worker startup
- Lint, type-check, unit, integration, API, frontend, and end-to-end tests
- Authorization checks for every role
- File upload, webhook, and export security tests
- Audit completeness review
- Critical query-plan review
- Failure and retry behavior tests
- Backup restoration procedure executed and verified

## Definition of Done

- No known critical or high-severity security issue remains
- All critical workflows pass end-to-end tests
- Required monitoring and alerting are active
- Backup restore has been tested successfully at least once

# PHASE 17 — STAGING DEPLOYMENT AND ACCEPTANCE TESTING

## Objective

Deploy the hardened system to a staging environment that closely resembles production and validate it end-to-end before any production launch.

## Scope

- Deploy dashboard (Vercel), API and worker (Railway), Supabase, Redis (Upstash), and Sentry staging configuration
- Run migrations and canonical staging seeds (including the 65-person dummy staff set and full menu/inventory/supplier fixtures)
- Validate every critical workflow against staging
- Run smoke, end-to-end, security, and performance tests against staging
- Resolve every release blocker found

## Definition of Done

- Staging mirrors the intended production topology
- Smoke tests, E2E tests, and security tests all pass in staging
- No unresolved release blocker remains

# PHASE 18 — PRODUCTION DEPLOYMENT AND LAUNCH

## Objective

Launch the production RKPR CRM in a controlled, verified, rollback-ready sequence.

## Scope

- Configure approved production domains and credentials (not invented in advance — see `DEPLOYMENT_AND_ENV.md`)
- Run production migrations as an explicit controlled step
- Deploy API, worker, and dashboard in the documented order
- Validate webhooks, integrations, queues, realtime, monitoring, backups, and alerts in production
- Execute production smoke tests
- Confirm rollback readiness before declaring launch complete

## Definition of Done

- Production smoke tests pass
- Monitoring, alerting, and backups are active and verified in production
- A documented, tested rollback path exists

# PHASE 19 — POST-LAUNCH STABILIZATION

## Objective

Stabilize the live system, close launch-related issues, and confirm operational readiness for ongoing use.

## Scope

- Monitor errors, latency, queue backlog, integration health, and user feedback
- Fix launch defects
- Tune performance and alert thresholds based on real production signal
- Validate backup and recovery operations under real conditions
- Close launch-related incidents and document lessons learned

## Definition of Done

- No open SEV-1/SEV-2 incident remains unresolved
- Performance and alerting are tuned to observed production behavior
- Lessons-learned notes are recorded

## 16. PHASE DEPENDENCY RULES

Phase 0 is mandatory before all later phases.

Phase 1 is mandatory before Phase 2 onward.

Phase 2 (database foundation) is mandatory before any phase that persists business data.

Phase 3 is mandatory before protected business features.

Phase 4 may begin after Phase 3, but its complete metrics depend on later modules populating real data.

Phase 5 (Customer and Lead CRM) must exist before reliable customer-linked orders, reservations, communications, loyalty, and feedback, and before safe lead conversion.

Phase 6 (Menu) must exist before Phase 7 (Orders) can reference real products, and before Phase 8 (Inventory) can map recipes to live consumption.

Phase 7 (Orders) must be integrated with Phase 8 (Inventory) before inventory reservation and consumption are considered complete.

Phase 9 (Reservations) depends on Phase 5 (Customers) and the notification foundation established across Phases 1–4.

Phase 10 (Communication Hub and Tasks) depends on Phase 5 (Customers and Leads), Phase 3 (authentication), and integration adapters introduced progressively through Phase 15.

Phase 11 (Knowledge Base and Staff Operations) depends on Phase 3 (authentication and role foundations) and file security established in Phase 1.

Phase 12 (Loyalty, Offers, and Campaigns) depends on Phase 5 (Customers), Phase 10 (Communications), consent handling, and background-job infrastructure from Phase 1/2.

Phase 13 (Feedback, Complaints, and Service Recovery) depends on Phase 7 (Orders) and Phase 9 (Reservations) as source events, and on Phase 5 for customer linkage.

Phase 14 (Reports, Analytics, and Controlled AI) depends on stable module data from Phases 5–13 and worker infrastructure from Phase 1/2.

Phase 15 (Integrations, Automations, Jobs, and Realtime) consolidates integrations and settings introduced conceptually by earlier phases and completes cross-module realtime/automation behavior.

Phase 16 (Security, Performance, and Quality Hardening) requires all selected production modules (Phases 1–15) to be functionally complete.

Phase 17 (Staging Deployment) requires Phase 16 to be complete.

Phase 18 (Production Deployment) requires Phase 17 to be complete and its blockers resolved.

Phase 19 (Post-Launch Stabilization) requires Phase 18 to be complete.

## 17. PROJECT-WIDE ACCEPTANCE RULES

Every collection endpoint is paginated and bounded.

Every large table is server-filtered, sorted, and paginated.

Every protected action is backend-authorized using the single canonical capability registry.

Every sensitive operation is audited.

Every status workflow uses explicit allowed transitions.

Every external integration has timeouts, retries where safe, deduplication, and visible failure states.

Every heavy report, export, campaign, file process, and AI task runs outside normal request handling, in the ARQ worker.

Every file is private by default and permission checked.

Every financial calculation is authoritative on the backend and stored as an integer minor unit.

Every module includes loading, empty, error, permission, disconnected, and large-data states where applicable.

Every phase must update tests and documentation, and must not be marked `COMPLETED` in `ROADMAP.md` until its Definition of Done passes.

A visually complete page using mock data is not considered complete.

## 18. FINAL PROJECT COMMAND

Build the RKPR Restaurant CRM one verified phase at a time, following the exact Phase 0–19 sequence defined in `ROADMAP.md`. Preserve all dummy data in this document for development and seeding until real client information is supplied. Do not invent unsupported integrations. Do not reduce security, performance, validation, auditability, or data integrity to complete phases faster. Do not proceed to the next phase until the current phase is demonstrably complete according to its Definition of Done.
