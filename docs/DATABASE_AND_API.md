# RKPR RESTAURANT CRM — DATABASE AND API

## 1. DOCUMENT PURPOSE

This document defines the authoritative database model and API contract for the RKPR Restaurant CRM. It must remain consistent with `CLAUDE.md`, `PROJECT_PLAN.md`, and `ARCHITECTURE_AND_TECH_STACK.md`.

The system is a private, single-business CRM for RKPR Fast-Food Restaurant. It is not multi-tenant. PostgreSQL is the durable source of truth. The FastAPI backend is the authoritative layer for validation, authorization, business rules, calculations, state transitions, and integrations.

Dummy data from `PROJECT_PLAN.md` may be used only for development, testing, demonstrations, fixtures, and seed data. It must never replace real architecture, provider choices, security decisions, or production configuration.

This document is the single canonical source for the capability/permission-code registry (§4.4) and the money-representation rule (§3.3). No other document may define a conflicting convention.

## 2. DATABASE PRINCIPLES

- PostgreSQL hosted in a dedicated Supabase project.
- SQLAlchemy 2.x for application data access, using the psycopg 3 driver.
- Alembic for migrations.
- UUID primary keys unless a later decision explicitly changes the strategy.
- Separate human-readable references for orders, leads, reports, suppliers, and other operational records.
- UTC timestamps using timezone-aware types.
- Backend-authoritative financial calculations.
- Integer minor-unit storage for money (see §3.3) — this is a closed decision, not an open choice.
- Foreign keys, unique constraints, check constraints, and non-null constraints for durable invariants.
- Soft deletion for recoverable business records.
- Append-oriented history tables and ledgers for traceability.
- Explicit allowed state transitions.
- Bounded queries, server-side pagination, indexed search, and query-pattern indexes.
- Transactions for multi-step business operations.
- Idempotency for duplicate-sensitive writes and provider events.
- No `tenant_id` columns unless the product architecture is explicitly changed.

## 3. CORE DATABASE CONVENTIONS

### 3.1 Common columns

Most mutable business tables should include:

- `id UUID PRIMARY KEY`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `created_by UUID NULL REFERENCES staff_users(id)` where useful
- `updated_by UUID NULL REFERENCES staff_users(id)` where useful
- `version INTEGER NOT NULL DEFAULT 1` for optimistic concurrency where needed
- `deleted_at TIMESTAMPTZ NULL` for soft-deletable entities
- `deleted_by UUID NULL REFERENCES staff_users(id)`
- `deletion_reason TEXT NULL`

Append-only ledgers and history tables do not require `updated_at` unless operational correction metadata is supported.

### 3.2 Naming

- Database tables and columns use `snake_case`.
- API JSON fields use `snake_case` unless a documented client-generation step requires another convention.
- Foreign keys use `<entity>_id`.
- Human-readable references use names such as `order_number`, `lead_number`, `supplier_code`, or `report_number`.
- Enum values use lowercase machine-safe strings such as `pending_review`.
- Permission/capability codes use lowercase, dot-separated strings — see §4.4.

### 3.3 Money — final, locked representation

This is a closed decision. Use exactly this convention everywhere in the project:

- All monetary values are stored as **integer minor units in `BIGINT` columns**.
- Column and field names always end in `_minor`, for example `price_minor`, `subtotal_minor`, `tax_minor`, `discount_minor`, `packaging_minor`, `delivery_minor`, `total_minor`, `refund_minor`, `amount_minor`, `unit_cost_minor`, `base_price_minor`, `lifetime_value_minor`.
- Never use binary floating-point types for money.
- `NUMERIC(14,2)` is **not** an approved alternative — do not present it as an open choice anywhere.
- API payloads use the same integer minor units for authoritative monetary values. Frontend formatting may display rupees and paise, but the frontend is never the calculation authority.
- Currency is stored where the domain requires it (`currency_code CHAR(3)`); the default dummy currency is INR.
- Rounding rules are deterministic and backend-owned.

### 3.4 Time

- All timestamps stored in UTC.
- Restaurant display timezone configured as `Asia/Kolkata`.
- Calendar dates may use `DATE` when the business concept is date-only.
- Time-of-day business settings may use `TIME` plus timezone configuration.

## 4. AUTHENTICATION, STAFF, ROLES, AND PERMISSIONS

### 4.1 `staff_users`

Purpose: Internal CRM user profile mapped to Supabase Auth identity.

Columns:

- `id UUID PRIMARY KEY`
- `auth_user_id UUID NOT NULL UNIQUE`
- `employee_code VARCHAR(32) NOT NULL UNIQUE`
- `first_name VARCHAR(80) NOT NULL`
- `last_name VARCHAR(80) NULL`
- `display_name VARCHAR(160) NOT NULL`
- `email CITEXT NOT NULL UNIQUE`
- `phone_e164 VARCHAR(20) NULL`
- `department_id UUID NULL REFERENCES departments(id)`
- `job_title VARCHAR(120) NULL`
- `account_status VARCHAR(32) NOT NULL`
- `employment_status VARCHAR(32) NOT NULL`
- `is_privileged BOOLEAN NOT NULL DEFAULT FALSE`
- `last_login_at TIMESTAMPTZ NULL`
- `timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata'`
- `avatar_storage_path VARCHAR(500) NULL` — private Supabase Storage object path, never a public URL; added during Phase 3 implementation as a natural profile field, consistent with the file-security rules in `SECURITY_PERFORMANCE_AND_QUALITY.md` §9
- `preferred_language VARCHAR(16) NULL` — added during Phase 3 implementation, mirroring the same field already present on `customers` (§6.1)
- common audit and soft-delete columns

Allowed `account_status` values:

- `invited`
- `active`
- `suspended`
- `disabled`
- `locked`
- `archived`

Fixed during Phase 3: this list previously omitted `archived`, while `SECURITY_PERFORMANCE_AND_QUALITY.md` §3.6 already listed it as an approved account state. `archived` is now included here so there is one enum, enforced by a single `CHECK` constraint, matching both documents. Like `disabled`, `suspended`, and `locked`, an `archived` account must not receive active CRM access.

Allowed `employment_status` values (not previously enumerated; added during Phase 3 implementation):

- `full_time`
- `part_time`
- `contract`
- `intern`

Indexes:

- unique `auth_user_id`
- unique active normalized email
- index on `department_id`
- partial index on active users

The canonical development seed set for `staff_users` is the 65-person dummy staff structure defined in `PROJECT_PLAN.md` §4.

### 4.2 `departments`

Examples:

- Leadership
- Operations
- Kitchen
- Inventory
- Reservations
- Customer Support
- Marketing
- Finance
- HR
- Delivery

Columns:

- `id UUID PRIMARY KEY`
- `code VARCHAR(32) NOT NULL UNIQUE`
- `name VARCHAR(100) NOT NULL UNIQUE`
- `description TEXT NULL`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- common columns

### 4.3 `roles`

Columns:

- `id UUID PRIMARY KEY`
- `code VARCHAR(64) NOT NULL UNIQUE`
- `name VARCHAR(120) NOT NULL`
- `description TEXT NULL`
- `is_system_role BOOLEAN NOT NULL DEFAULT FALSE`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- common columns

Seed role codes must match `PROJECT_PLAN.md`:

- `owner`
- `general_manager`
- `operations_manager`
- `finance_manager`
- `kitchen_manager`
- `inventory_manager`
- `reservation_manager`
- `customer_support_agent`
- `marketing_manager`
- `hr_manager`
- `shift_supervisor`
- `kitchen_staff`
- `front_of_house_staff`
- `delivery_coordinator`
- `read_only_auditor`

### 4.4 `permissions` — the single canonical capability registry

Columns:

- `id UUID PRIMARY KEY`
- `code VARCHAR(120) NOT NULL UNIQUE`
- `module VARCHAR(64) NOT NULL`
- `action VARCHAR(64) NOT NULL`
- `description TEXT NULL`
- `is_sensitive BOOLEAN NOT NULL DEFAULT FALSE`

**Canonical permission-code format** (this is the one and only naming convention used across every document and all future code):

- lowercase
- dot-separated
- domain first, action or sub-action after the domain
- no spaces, no camelCase, no inconsistent synonyms (never use a different name for the same action in two places)

Representative examples — the complete registry is represented in code from this single source and tested for uniqueness:

- `dashboard.view`
- `customers.view`
- `customers.create`
- `customers.update`
- `customers.merge`
- `customers.export`
- `leads.view`
- `leads.create`
- `leads.update`
- `leads.assign`
- `leads.transition`
- `orders.view`
- `orders.create`
- `orders.update`
- `orders.transition`
- `orders.discount.apply`
- `orders.cancel.request`
- `orders.cancel.approve`
- `orders.refund.request`
- `orders.refund.approve`
- `inventory.view`
- `inventory.adjust`
- `inventory.receive`
- `inventory.transfer`
- `reservations.view`
- `reservations.create`
- `reservations.update`
- `reservations.approve`
- `reservations.transition`
- `staff.view`
- `staff.manage`
- `staff.hr_sensitive.read`
- `roles.view`
- `roles.manage`
- `campaigns.view`
- `campaigns.create`
- `campaigns.approve`
- `campaigns.send`
- `reports.view`
- `reports.export`
- `settings.view`
- `settings.manage`
- `settings.integrations.update`
- `audit.view`

Backend authorization is mandatory for every one of these even when the UI hides the corresponding action. Do not introduce a differently-shaped synonym (for example `orders.update_status` instead of `orders.transition`, generic `orders.refund` instead of `orders.refund.request` / `orders.refund.approve`, or vague `leads.manage` instead of the specific `leads.*` actions above) in any other document, migration, or code path.

### 4.5 Mapping tables

`role_permissions`

- `role_id UUID REFERENCES roles(id)`
- `permission_id UUID REFERENCES permissions(id)`
- `scope_type VARCHAR(32) NOT NULL DEFAULT 'all'`
- composite primary key on role and permission

`staff_roles`

- `staff_user_id UUID REFERENCES staff_users(id)`
- `role_id UUID REFERENCES roles(id)`
- `assigned_by UUID REFERENCES staff_users(id)`
- `assigned_at TIMESTAMPTZ NOT NULL`
- composite primary key on staff and role

Scope types may include:

- `all`
- `department`
- `assigned`
- `self`
- `none`

Phase 3 evaluates the `all` and `none` scopes only, since no scoped business records (leads, orders, reservations, and so on) exist yet. `department`, `assigned`, and `self` scoping is enforced by the modules that own those records starting in later phases; the column exists now so those modules do not require a migration to add it.

### 4.6 `staff_invitations` — added during Phase 3 implementation

`PROJECT_PLAN.md` Phase 3 lists "Invitation records" as a database task without defining the table shape; this section is the definition, added when the invitation workflow was implemented.

Purpose: track the CRM's own record of who was invited, to which role and department, and by whom — separate from Supabase Auth's own invitation-token delivery, which this table does not duplicate.

Columns:

- `id UUID PRIMARY KEY`
- `email CITEXT NOT NULL`
- `first_name VARCHAR(80) NOT NULL`
- `last_name VARCHAR(80) NULL`
- `department_id UUID NULL REFERENCES departments(id)`
- `intended_role_id UUID NOT NULL REFERENCES roles(id)`
- `invited_by UUID NOT NULL REFERENCES staff_users(id)`
- `status VARCHAR(32) NOT NULL DEFAULT 'pending'` (`pending`, `accepted`, `revoked`, `expired`)
- `invited_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `expires_at TIMESTAMPTZ NOT NULL`
- `accepted_at TIMESTAMPTZ NULL`
- `revoked_at TIMESTAMPTZ NULL`
- `staff_user_id UUID NULL REFERENCES staff_users(id)` — filled in once the invitation is accepted and the `staff_users` row exists
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Acceptance is provisioned on first authenticated request from the invited identity (see `ARCHITECTURE_AND_TECH_STACK.md` §10.1 step 6), not through a separate webhook, since the backend already verifies the token on every request.

## 5. RESTAURANT CONFIGURATION

### 5.1 `restaurant_profile`

Single active row for RKPR.

Columns:

- `id UUID PRIMARY KEY`
- `restaurant_name VARCHAR(160) NOT NULL`
- `display_brand VARCHAR(80) NOT NULL`
- `legal_business_name VARCHAR(200) NULL`
- `business_type VARCHAR(120) NULL`
- `primary_cuisine TEXT NULL`
- `gstin VARCHAR(32) NULL`
- `fssai_license_number VARCHAR(32) NULL`
- `pan VARCHAR(16) NULL`
- `establishment_code VARCHAR(64) NULL`
- `address_line_1 VARCHAR(200) NOT NULL`
- `address_line_2 VARCHAR(200) NULL`
- `locality VARCHAR(120) NULL`
- `city VARCHAR(120) NOT NULL`
- `state VARCHAR(120) NOT NULL`
- `postal_code VARCHAR(16) NOT NULL`
- `country_code CHAR(2) NOT NULL DEFAULT 'IN'`
- `latitude NUMERIC(9,6) NULL`
- `longitude NUMERIC(9,6) NULL`
- `primary_phone_e164 VARCHAR(20) NULL`
- `reservation_phone_e164 VARCHAR(20) NULL`
- `whatsapp_phone_e164 VARCHAR(20) NULL`
- `kitchen_phone_e164 VARCHAR(20) NULL`
- `owner_escalation_phone_e164 VARCHAR(20) NULL`
- `general_email CITEXT NULL`
- `orders_email CITEXT NULL`
- `reservations_email CITEXT NULL`
- `support_email CITEXT NULL`
- `owner_reports_email CITEXT NULL`
- `website_url TEXT NULL`
- `instagram_handle VARCHAR(120) NULL`
- `facebook_page VARCHAR(160) NULL`
- `timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata'`
- `currency_code CHAR(3) NOT NULL DEFAULT 'INR'`
- common columns

Development seed values must exactly match `PROJECT_PLAN.md`, including the dummy address, contacts, and identifiers.

### 5.2 `operating_hours`

Columns:

- `id UUID PRIMARY KEY`
- `day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6)`
- `opens_at TIME NULL`
- `closes_at TIME NULL`
- `is_closed BOOLEAN NOT NULL DEFAULT FALSE`
- `service_type VARCHAR(32) NOT NULL DEFAULT 'general'`
- `last_dine_in_order_minutes_before_close INTEGER NULL`
- `last_delivery_order_minutes_before_close INTEGER NULL`
- common columns

Unique constraint on day and service type.

### 5.3 `restaurant_tables`

Columns:

- `id UUID PRIMARY KEY`
- `table_code VARCHAR(32) NOT NULL UNIQUE`
- `seating_zone VARCHAR(64) NOT NULL`
- `capacity INTEGER NOT NULL CHECK (capacity > 0)`
- `is_accessible BOOLEAN NOT NULL DEFAULT FALSE`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- `merge_group VARCHAR(64) NULL`
- common columns

## 6. CUSTOMERS

### 6.1 `customers`

Columns:

- `id UUID PRIMARY KEY`
- `customer_number VARCHAR(32) NOT NULL UNIQUE`
- `customer_type VARCHAR(32) NOT NULL DEFAULT 'individual'`
- `first_name VARCHAR(100) NULL`
- `last_name VARCHAR(100) NULL`
- `organization_name VARCHAR(180) NULL`
- `display_name VARCHAR(200) NOT NULL`
- `primary_phone_e164 VARCHAR(20) NULL`
- `primary_email CITEXT NULL`
- `date_of_birth DATE NULL`
- `anniversary_date DATE NULL`
- `preferred_language VARCHAR(16) NULL`
- `dietary_preference VARCHAR(32) NULL`
- `spice_preference VARCHAR(32) NULL`
- `customer_status VARCHAR(32) NOT NULL DEFAULT 'active'`
- `customer_segment VARCHAR(32) NULL`
- `acquisition_source VARCHAR(64) NULL`
- `assigned_staff_id UUID NULL REFERENCES staff_users(id)`
- `first_order_at TIMESTAMPTZ NULL`
- `last_order_at TIMESTAMPTZ NULL`
- `completed_order_count INTEGER NOT NULL DEFAULT 0`
- `lifetime_value_minor BIGINT NOT NULL DEFAULT 0`
- `average_order_value_minor BIGINT NOT NULL DEFAULT 0`
- `last_activity_at TIMESTAMPTZ NULL`
- common columns

Customer segments must remain consistent with `PROJECT_PLAN.md`:

- `new`
- `repeat`
- `loyal`
- `vip`
- `at_risk`
- `dormant`
- `high_aov`
- `family`
- `corporate`
- `college_group`
- `delivery_first`
- `dine_in_first`
- `discount_sensitive`
- `complaint_recovery`

Indexes:

- normalized phone
- normalized email
- status and segment
- assigned staff
- last order date
- partial index for active non-deleted customers

### 6.2 `customer_addresses`

- `id UUID PRIMARY KEY`
- `customer_id UUID NOT NULL REFERENCES customers(id)`
- `label VARCHAR(64) NULL`
- address fields
- `latitude NUMERIC(9,6) NULL`
- `longitude NUMERIC(9,6) NULL`
- `delivery_instructions TEXT NULL`
- `is_default BOOLEAN NOT NULL DEFAULT FALSE`
- common columns

### 6.3 `customer_preferences`

- `id UUID PRIMARY KEY`
- `customer_id UUID NOT NULL UNIQUE REFERENCES customers(id)`
- `vegetarian BOOLEAN NOT NULL DEFAULT FALSE`
- `vegan BOOLEAN NOT NULL DEFAULT FALSE`
- `jain BOOLEAN NOT NULL DEFAULT FALSE`
- `allergen_notes TEXT NULL`
- `favorite_product_id UUID NULL REFERENCES products(id)`
- `preferred_order_channel VARCHAR(32) NULL`
- `preferred_seating_zone VARCHAR(64) NULL`
- `notes TEXT NULL`
- common columns

### 6.4 `customer_notes`

- `id UUID PRIMARY KEY`
- `customer_id UUID NOT NULL REFERENCES customers(id)`
- `note_type VARCHAR(32) NOT NULL DEFAULT 'general'`
- `content TEXT NOT NULL`
- `is_sensitive BOOLEAN NOT NULL DEFAULT FALSE`
- `created_by UUID NOT NULL REFERENCES staff_users(id)`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

### 6.5 `tags` and `customer_tags`

`tags` stores normalized reusable tags.

`customer_tags` links customers to tags with assignment metadata.

### 6.6 `customer_consents`

Columns:

- `id UUID PRIMARY KEY`
- `customer_id UUID NOT NULL REFERENCES customers(id)`
- `consent_type VARCHAR(64) NOT NULL`
- `status VARCHAR(32) NOT NULL`
- `source VARCHAR(64) NOT NULL`
- `policy_version VARCHAR(64) NULL`
- `captured_text TEXT NULL`
- `granted_at TIMESTAMPTZ NULL`
- `withdrawn_at TIMESTAMPTZ NULL`
- `evidence_metadata JSONB NULL`
- common columns

Consent types:

- `whatsapp_marketing`
- `email_marketing`
- `sms_marketing`
- `loyalty`
- `feedback_request`
- `personalization`

Unique constraint on active consent record per customer and type, or maintain append-only history with one current pointer.

### 6.7 `customer_merge_events`

Stores source customer IDs, surviving customer ID, actor, reason, mapping summary, and timestamp. Merge must occur in one transaction.

## 7. LEADS

### 7.1 `leads`

Columns:

- `id UUID PRIMARY KEY`
- `lead_number VARCHAR(32) NOT NULL UNIQUE`
- `lead_type VARCHAR(32) NOT NULL`
- `display_name VARCHAR(200) NOT NULL`
- `organization_name VARCHAR(200) NULL`
- `contact_name VARCHAR(160) NULL`
- `phone_e164 VARCHAR(20) NULL`
- `email CITEXT NULL`
- `source VARCHAR(64) NOT NULL`
- `campaign_id UUID NULL REFERENCES campaigns(id)`
- `status VARCHAR(32) NOT NULL DEFAULT 'new'`
- `priority VARCHAR(16) NOT NULL DEFAULT 'normal'`
- `estimated_value_minor BIGINT NULL`
- `party_size INTEGER NULL`
- `requested_date DATE NULL`
- `requested_time TIME NULL`
- `assigned_staff_id UUID NULL REFERENCES staff_users(id)`
- `next_follow_up_at TIMESTAMPTZ NULL`
- `won_customer_id UUID NULL REFERENCES customers(id)`
- `lost_reason VARCHAR(120) NULL`
- `description TEXT NULL`
- common columns

Allowed sources remain consistent with `PROJECT_PLAN.md`:

- `website`
- `phone`
- `walk_in`
- `whatsapp`
- `zomato_import`
- `swiggy_import`
- `meta_campaign`
- `google_campaign`
- `referral`
- `corporate_outreach`
- `event_enquiry`
- `offline_qr`

Allowed statuses:

- `new`
- `contacted`
- `qualified`
- `interested`
- `follow_up_scheduled`
- `proposal_shared`
- `negotiating`
- `won`
- `lost`
- `closed`

Indexes:

- status and created time
- source and created time
- assigned staff and next follow-up
- requested date
- active non-deleted leads

### 7.2 `lead_activities`

- `id UUID PRIMARY KEY`
- `lead_id UUID NOT NULL REFERENCES leads(id)`
- `activity_type VARCHAR(64) NOT NULL`
- `summary TEXT NOT NULL`
- `metadata JSONB NULL`
- `performed_by UUID NULL REFERENCES staff_users(id)`
- `occurred_at TIMESTAMPTZ NOT NULL`

### 7.3 `lead_status_history`

Append-only:

- previous status
- new status
- actor
- reason
- timestamp

### 7.4 `lead_follow_ups`

- `id UUID PRIMARY KEY`
- `lead_id UUID NOT NULL REFERENCES leads(id)`
- `assigned_to UUID NOT NULL REFERENCES staff_users(id)`
- `scheduled_at TIMESTAMPTZ NOT NULL`
- `status VARCHAR(32) NOT NULL`
- `completed_at TIMESTAMPTZ NULL`
- `outcome TEXT NULL`
- common columns

## 8. MENU AND PRODUCTS

### 8.1 `menu_categories`

Seed categories consistent with `PROJECT_PLAN.md`:

- Burgers
- Pizzas
- Tacos
- Burritos and Bowls
- Sides
- Beverages
- Desserts
- Combos

Columns:

- `id UUID PRIMARY KEY`
- `code VARCHAR(64) NOT NULL UNIQUE`
- `name VARCHAR(120) NOT NULL`
- `description TEXT NULL`
- `sort_order INTEGER NOT NULL DEFAULT 0`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- common columns

### 8.2 `products`

Columns:

- `id UUID PRIMARY KEY`
- `product_code VARCHAR(64) NOT NULL UNIQUE`
- `category_id UUID NOT NULL REFERENCES menu_categories(id)`
- `name VARCHAR(180) NOT NULL`
- `slug VARCHAR(180) NOT NULL UNIQUE`
- `description TEXT NULL`
- `food_type VARCHAR(32) NOT NULL`
- `is_jain_capable BOOLEAN NOT NULL DEFAULT FALSE`
- `is_vegan_capable BOOLEAN NOT NULL DEFAULT FALSE`
- `preparation_minutes INTEGER NULL`
- `calories INTEGER NULL`
- `base_price_minor BIGINT NOT NULL CHECK (base_price_minor >= 0)`
- `tax_category VARCHAR(64) NULL`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- `is_available BOOLEAN NOT NULL DEFAULT TRUE`
- `availability_source VARCHAR(32) NOT NULL DEFAULT 'manual'`
- `manual_override_until TIMESTAMPTZ NULL`
- `manual_override_reason TEXT NULL`
- `image_storage_path TEXT NULL`
- common columns

All menu seeds must exactly match the names and dummy prices in `PROJECT_PLAN.md`, including:

- RKPR Classic Veg Burger — ₹179
- RKPR Spicy Paneer Burger — ₹229
- Smoky BBQ Chicken Burger — ₹259
- Double Crunch Chicken Burger — ₹299
- Jain Aloo Crunch Burger — ₹189
- Margherita Pizza variants
- Farmhouse Veg Pizza variants
- Paneer Tikka Pizza variants
- BBQ Chicken Pizza variants
- Mexican Fire Pizza variants
- tacos, burritos, bowls, sides, beverages, desserts, combos, and add-ons listed in `PROJECT_PLAN.md`

### 8.3 `product_variants`

- `id UUID PRIMARY KEY`
- `product_id UUID NOT NULL REFERENCES products(id)`
- `code VARCHAR(64) NOT NULL UNIQUE`
- `name VARCHAR(120) NOT NULL`
- `price_minor BIGINT NOT NULL`
- `sort_order INTEGER NOT NULL DEFAULT 0`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- common columns

Use variants for 8-inch and 11-inch pizzas where appropriate.

### 8.4 `modifier_groups`

- `id UUID PRIMARY KEY`
- `name VARCHAR(120) NOT NULL`
- `min_select INTEGER NOT NULL DEFAULT 0`
- `max_select INTEGER NOT NULL DEFAULT 1`
- `is_required BOOLEAN NOT NULL DEFAULT FALSE`
- common columns

### 8.5 `modifiers`

Seed modifiers consistent with `PROJECT_PLAN.md`:

- Cheese slice — ₹35
- Extra paneer patty — ₹80
- Extra chicken patty — ₹100
- Extra vegetable patty — ₹60
- Jalapeños — ₹25
- Extra sauce — ₹20
- Gluten-aware bun substitute — ₹60
- Make it Jain — no charge where possible
- Make it extra spicy — no charge
- Remove ingredient — no charge

### 8.6 Product-modifier mapping

Use `product_modifier_groups` and `modifier_group_items` with sort order, availability, and optional channel-specific pricing.

## 9. RECIPES, INVENTORY, AND SUPPLIERS

### 9.1 `inventory_items`

Columns:

- `id UUID PRIMARY KEY`
- `item_code VARCHAR(64) NOT NULL UNIQUE`
- `name VARCHAR(180) NOT NULL`
- `category VARCHAR(64) NOT NULL`
- `storage_zone VARCHAR(64) NOT NULL`
- `unit_of_measure VARCHAR(32) NOT NULL`
- `current_stock NUMERIC(16,3) NOT NULL DEFAULT 0`
- `reserved_stock NUMERIC(16,3) NOT NULL DEFAULT 0`
- `reorder_level NUMERIC(16,3) NOT NULL DEFAULT 0`
- `target_stock NUMERIC(16,3) NOT NULL DEFAULT 0`
- `maximum_stock NUMERIC(16,3) NULL`
- `average_unit_cost_minor BIGINT NULL`
- `preferred_supplier_id UUID NULL REFERENCES suppliers(id)`
- `alternative_supplier_id UUID NULL REFERENCES suppliers(id)`
- `lead_time_days INTEGER NULL`
- `shelf_life_days INTEGER NULL`
- `requires_batch_tracking BOOLEAN NOT NULL DEFAULT FALSE`
- `requires_expiry_tracking BOOLEAN NOT NULL DEFAULT FALSE`
- `allergen_flags TEXT[] NULL`
- `stock_status VARCHAR(32) NOT NULL DEFAULT 'in_stock'`
- `last_counted_at TIMESTAMPTZ NULL`
- `last_received_at TIMESTAMPTZ NULL`
- common columns

Allowed stock statuses:

- `in_stock`
- `low_stock`
- `critical_stock`
- `out_of_stock`
- `reserved`
- `quarantined`
- `expired`
- `damaged`
- `under_count_review`
- `discontinued`

Seed stock values must match `PROJECT_PLAN.md`, including burger buns, patties, mozzarella, cheddar, paneer, chicken, fries, taco shells, tortillas, vegetables, sauces, beverages, desserts, and packaging.

### 9.2 `inventory_batches`

- `id UUID PRIMARY KEY`
- `inventory_item_id UUID NOT NULL REFERENCES inventory_items(id)`
- `batch_code VARCHAR(80) NOT NULL`
- `supplier_id UUID NULL REFERENCES suppliers(id)`
- `received_quantity NUMERIC(16,3) NOT NULL`
- `remaining_quantity NUMERIC(16,3) NOT NULL`
- `received_at TIMESTAMPTZ NOT NULL`
- `manufactured_at DATE NULL`
- `expires_at DATE NULL`
- `status VARCHAR(32) NOT NULL`
- `unit_cost_minor BIGINT NULL`
- unique item and batch code

### 9.3 `stock_movements`

Append-only ledger:

- `id UUID PRIMARY KEY`
- `inventory_item_id UUID NOT NULL REFERENCES inventory_items(id)`
- `batch_id UUID NULL REFERENCES inventory_batches(id)`
- `movement_type VARCHAR(64) NOT NULL`
- `quantity_delta NUMERIC(16,3) NOT NULL`
- `unit_cost_minor BIGINT NULL`
- `reference_type VARCHAR(64) NULL`
- `reference_id UUID NULL`
- `reason TEXT NULL`
- `performed_by UUID NULL REFERENCES staff_users(id)`
- `occurred_at TIMESTAMPTZ NOT NULL`
- `idempotency_key VARCHAR(160) NULL UNIQUE`

Movement types must match `PROJECT_PLAN.md`, including purchase receipt, kitchen issue, recipe consumption, adjustment, waste, damage, expiry, return, transfer, count correction, reservation, and release.

### 9.4 `recipes`

- `id UUID PRIMARY KEY`
- `product_id UUID NOT NULL REFERENCES products(id)`
- `variant_id UUID NULL REFERENCES product_variants(id)`
- `version INTEGER NOT NULL`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- `effective_from TIMESTAMPTZ NOT NULL`
- `effective_to TIMESTAMPTZ NULL`
- common columns

### 9.5 `recipe_items`

- `recipe_id UUID NOT NULL REFERENCES recipes(id)`
- `inventory_item_id UUID NOT NULL REFERENCES inventory_items(id)`
- `quantity_required NUMERIC(16,3) NOT NULL`
- `waste_factor NUMERIC(8,4) NOT NULL DEFAULT 0`
- composite primary key on recipe and inventory item

### 9.6 `suppliers`

Columns:

- `id UUID PRIMARY KEY`
- `supplier_code VARCHAR(32) NOT NULL UNIQUE`
- `name VARCHAR(180) NOT NULL`
- `contact_person VARCHAR(160) NULL`
- `phone_e164 VARCHAR(20) NULL`
- `email CITEXT NULL`
- address fields
- `supply_categories TEXT[] NULL`
- `normal_lead_time_days INTEGER NULL`
- `payment_terms VARCHAR(120) NULL`
- `minimum_order_value_minor BIGINT NULL`
- `status VARCHAR(32) NOT NULL DEFAULT 'active'`
- common columns

Supplier seed records must exactly match the dummy suppliers from `PROJECT_PLAN.md`, including:

- Bengaluru Bakers Supply
- Nandi Dairy Foods
- Southern Poultry Co.
- GreenLeaf Produce
- FrostBite Distributors
- MexiSource India
- TasteCraft Condiments
- EcoPack Bengaluru

### 9.7 Purchase receiving

Use:

- `purchase_orders`
- `purchase_order_items`
- `goods_receipts`
- `goods_receipt_items`

All receipt operations must create stock movements transactionally.

## 10. ORDERS

### 10.1 `orders`

Columns:

- `id UUID PRIMARY KEY`
- `order_number VARCHAR(40) NOT NULL UNIQUE`
- `customer_id UUID NULL REFERENCES customers(id)`
- `source VARCHAR(32) NOT NULL`
- `order_type VARCHAR(32) NOT NULL`
- `status VARCHAR(32) NOT NULL`
- `payment_status VARCHAR(32) NOT NULL`
- `fulfilment_status VARCHAR(32) NOT NULL`
- `assigned_staff_id UUID NULL REFERENCES staff_users(id)`
- `delivery_address_id UUID NULL REFERENCES customer_addresses(id)`
- `currency_code CHAR(3) NOT NULL DEFAULT 'INR'`
- `subtotal_minor BIGINT NOT NULL`
- `discount_minor BIGINT NOT NULL DEFAULT 0`
- `tax_minor BIGINT NOT NULL DEFAULT 0`
- `packaging_minor BIGINT NOT NULL DEFAULT 0`
- `delivery_minor BIGINT NOT NULL DEFAULT 0`
- `loyalty_discount_minor BIGINT NOT NULL DEFAULT 0`
- `total_minor BIGINT NOT NULL`
- `customer_notes TEXT NULL`
- `internal_notes TEXT NULL`
- `accepted_at TIMESTAMPTZ NULL`
- `preparing_at TIMESTAMPTZ NULL`
- `ready_at TIMESTAMPTZ NULL`
- `picked_up_at TIMESTAMPTZ NULL`
- `out_for_delivery_at TIMESTAMPTZ NULL`
- `delivered_at TIMESTAMPTZ NULL`
- `cancelled_at TIMESTAMPTZ NULL`
- `cancellation_reason TEXT NULL`
- `external_order_id VARCHAR(160) NULL`
- `idempotency_key VARCHAR(160) NULL UNIQUE`
- common columns

Order sources:

- `website`
- `mobile_web`
- `whatsapp_assisted`
- `phone_assisted`
- `pos_import`
- `zomato_import`
- `swiggy_import`
- `corporate`
- `event`

Allowed order statuses remain consistent with `PROJECT_PLAN.md`:

- `draft`
- `pending_payment`
- `payment_verification_pending`
- `confirmed`
- `accepted`
- `preparing`
- `quality_check`
- `ready`
- `picked_up`
- `out_for_delivery`
- `delivered`
- `cancelled`
- `refund_requested`
- `refund_processing`
- `refunded`
- `failed`

### 10.2 `order_items`

- `id UUID PRIMARY KEY`
- `order_id UUID NOT NULL REFERENCES orders(id)`
- `product_id UUID NOT NULL REFERENCES products(id)`
- `variant_id UUID NULL REFERENCES product_variants(id)`
- `product_name_snapshot VARCHAR(180) NOT NULL`
- `variant_name_snapshot VARCHAR(120) NULL`
- `quantity INTEGER NOT NULL CHECK (quantity > 0)`
- `unit_price_minor BIGINT NOT NULL`
- `line_discount_minor BIGINT NOT NULL DEFAULT 0`
- `line_tax_minor BIGINT NOT NULL DEFAULT 0`
- `line_total_minor BIGINT NOT NULL`
- `special_instructions TEXT NULL`
- `recipe_version INTEGER NULL`

### 10.3 `order_item_modifiers`

Stores modifier snapshots, price, quantity, and customer instructions.

### 10.4 `order_status_history`

Append-only with previous status, new status, actor, timestamp, reason, source, and correlation ID.

### 10.5 Payments and refunds

Use:

- `payments`
- `payment_events`
- `refunds`
- `refund_events`

Provider IDs and webhook event IDs must be unique. Duplicate webhook events must not duplicate financial effects.

### 10.6 Inventory reservations

Use `inventory_reservations` with:

- order ID
- inventory item ID
- reserved quantity
- consumed quantity
- released quantity
- state
- idempotency key

Reservation, consumption, and release must be transaction-safe.

## 11. RESERVATIONS

### 11.1 `reservations`

Columns:

- `id UUID PRIMARY KEY`
- `reservation_number VARCHAR(40) NOT NULL UNIQUE`
- `customer_id UUID NULL REFERENCES customers(id)`
- `guest_name VARCHAR(180) NOT NULL`
- `phone_e164 VARCHAR(20) NULL`
- `email CITEXT NULL`
- `reservation_date DATE NOT NULL`
- `start_time TIME NOT NULL`
- `end_time TIME NULL`
- `guest_count INTEGER NOT NULL CHECK (guest_count > 0)`
- `seating_zone VARCHAR(64) NULL`
- `status VARCHAR(32) NOT NULL DEFAULT 'requested'`
- `approval_status VARCHAR(32) NOT NULL DEFAULT 'pending_review'`
- `special_requests TEXT NULL`
- `assigned_staff_id UUID NULL REFERENCES staff_users(id)`
- `approved_by UUID NULL REFERENCES staff_users(id)`
- `approved_at TIMESTAMPTZ NULL`
- `rejected_by UUID NULL REFERENCES staff_users(id)`
- `rejected_at TIMESTAMPTZ NULL`
- `rejection_reason TEXT NULL`
- `arrived_at TIMESTAMPTZ NULL`
- `seated_at TIMESTAMPTZ NULL`
- `completed_at TIMESTAMPTZ NULL`
- `cancelled_at TIMESTAMPTZ NULL`
- `cancellation_source VARCHAR(32) NULL`
- common columns

Statuses must remain consistent with `PROJECT_PLAN.md`:

- `requested`
- `pending_review`
- `needs_clarification`
- `approved`
- `rejected`
- `confirmation_sending`
- `confirmed`
- `reminder_scheduled`
- `arrived`
- `seated`
- `completed`
- `no_show`
- `cancelled_by_customer`
- `cancelled_by_restaurant`

No automatic approval is allowed in the initial system.

### 11.2 `reservation_table_assignments`

- `reservation_id UUID REFERENCES reservations(id)`
- `restaurant_table_id UUID REFERENCES restaurant_tables(id)`
- `assigned_at TIMESTAMPTZ NOT NULL`
- `assigned_by UUID REFERENCES staff_users(id)`
- composite primary key

### 11.3 `reservation_status_history`

Append-only state history.

### 11.4 `reservation_reminders`

Tracks scheduled, sent, failed, cancelled, and retry states.

## 12. COMMUNICATION HUB

### 12.1 `conversations`

- `id UUID PRIMARY KEY`
- `conversation_number VARCHAR(40) NOT NULL UNIQUE`
- `channel VARCHAR(32) NOT NULL`
- `customer_id UUID NULL REFERENCES customers(id)`
- `lead_id UUID NULL REFERENCES leads(id)`
- `subject VARCHAR(200) NULL`
- `status VARCHAR(32) NOT NULL DEFAULT 'open'`
- `assigned_staff_id UUID NULL REFERENCES staff_users(id)`
- `last_message_at TIMESTAMPTZ NULL`
- `unread_count INTEGER NOT NULL DEFAULT 0`
- common columns

### 12.2 `messages`

- `id UUID PRIMARY KEY`
- `conversation_id UUID NOT NULL REFERENCES conversations(id)`
- `channel VARCHAR(32) NOT NULL`
- `direction VARCHAR(16) NOT NULL`
- `sender_reference VARCHAR(200) NULL`
- `recipient_reference VARCHAR(200) NULL`
- `provider_message_id VARCHAR(200) NULL`
- `message_type VARCHAR(32) NOT NULL`
- `body_text TEXT NULL`
- `delivery_status VARCHAR(32) NOT NULL`
- `template_id UUID NULL REFERENCES communication_templates(id)`
- `sent_at TIMESTAMPTZ NULL`
- `delivered_at TIMESTAMPTZ NULL`
- `read_at TIMESTAMPTZ NULL`
- `failed_at TIMESTAMPTZ NULL`
- `failure_code VARCHAR(120) NULL`
- `failure_message TEXT NULL`
- `created_by UUID NULL REFERENCES staff_users(id)`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Unique provider message ID where non-null.

### 12.3 `message_attachments`

Stores private storage path, filename, MIME type, size, scan status, and permission metadata.

### 12.4 `communication_templates`

Stores channel, provider template ID, language, category, active state, body structure, and version.

## 13. KNOWLEDGE BASE

### 13.1 `knowledge_folders`

- `id UUID PRIMARY KEY`
- `parent_id UUID NULL REFERENCES knowledge_folders(id)`
- `name VARCHAR(180) NOT NULL`
- `description TEXT NULL`
- `sort_order INTEGER NOT NULL DEFAULT 0`
- common columns

### 13.2 `knowledge_documents`

- `id UUID PRIMARY KEY`
- `folder_id UUID NULL REFERENCES knowledge_folders(id)`
- `title VARCHAR(220) NOT NULL`
- `document_type VARCHAR(64) NOT NULL`
- `status VARCHAR(32) NOT NULL`
- `current_version_id UUID NULL`
- `owner_staff_id UUID NULL REFERENCES staff_users(id)`
- `search_text TSVECTOR NULL`
- common columns

### 13.3 `knowledge_document_versions`

Stores version number, private storage path, MIME type, size, checksum, uploaded by, scan state, extracted plain text where approved, and created time.

No embeddings, pgvector, semantic search, or RAG tables are allowed.

## 14. STAFF AND HR

### 14.1 `staff_profiles`

One-to-one with `staff_users` where the person has system access, but may also support non-login staff.

Stores:

- employee details
- department
- job title
- joining date
- employment status
- manager
- emergency contact
- shift eligibility
- restricted HR metadata

### 14.2 `staff_documents`

Private file metadata with strict permission controls.

### 14.3 `leave_requests`

- staff
- leave type
- start and end dates
- reason
- approval status
- reviewer
- decision timestamp

### 14.4 `training_records`

Stores training type, provider, completion date, expiry date, status, and reminders.

### 14.5 `shift_assignments`

Stores date, start, end, role, location, and assignment state.

## 15. LOYALTY, MARKETING, FEEDBACK, AND COMPLAINTS

### 15.1 `loyalty_accounts`

- `id UUID PRIMARY KEY`
- `customer_id UUID NOT NULL UNIQUE REFERENCES customers(id)`
- `status VARCHAR(32) NOT NULL`
- `current_points INTEGER NOT NULL DEFAULT 0`
- `lifetime_earned_points INTEGER NOT NULL DEFAULT 0`
- `lifetime_redeemed_points INTEGER NOT NULL DEFAULT 0`
- common columns

### 15.2 `loyalty_ledger`

Append-only:

- account
- entry type
- points delta
- `value_minor`
- source type and ID
- expiry date
- idempotency key
- actor
- timestamp

Rules must match `PROJECT_PLAN.md`:

- 1 point per ₹10 eligible direct spend
- 100 welcome points after first completed direct order
- 200 birthday points once per year when eligible
- 150 referral points after referred customer's first completed direct order
- minimum 300 points to redeem
- 100 points equals ₹25
- maximum redemption 20% of eligible subtotal
- 365-day expiry

### 15.3 `campaigns`

- `id UUID PRIMARY KEY`
- `campaign_number VARCHAR(40) NOT NULL UNIQUE`
- `name VARCHAR(180) NOT NULL`
- `channel VARCHAR(32) NOT NULL`
- `status VARCHAR(32) NOT NULL`
- `audience_definition JSONB NOT NULL`
- `scheduled_at TIMESTAMPTZ NULL`
- `started_at TIMESTAMPTZ NULL`
- `completed_at TIMESTAMPTZ NULL`
- `created_by UUID NOT NULL REFERENCES staff_users(id)`
- common columns

### 15.4 `campaign_recipients`

Stores audience snapshot, consent result, suppression reason, send status, provider ID, conversion references, and timestamps.

### 15.5 `feedback_entries`

Stores customer, order or reservation link, source, rating, comments, sentiment flag if used, resolution state, and timestamps.

### 15.6 `complaints`

Stores complaint number, customer, order or reservation reference, category, severity, status, assignee, SLA due time, description, resolution, recovery value, and history.

## 16. REPORTS, EXPORTS, NOTIFICATIONS, AUDIT, AND JOBS

### 16.1 `reports`

Stores report definition, period, status, generated file path, recipient snapshot, generated by, and timestamps.

### 16.2 `report_schedules`

Stores daily, weekly, or monthly cadence, timezone, recipients, enabled state, and next run.

Seed dummy recipients must match `PROJECT_PLAN.md` and remain configurable:

- owner@rkpr-demo.example
- manager@rkpr-demo.example
- finance@rkpr-demo.example

### 16.3 `export_requests`

Stores requester, export type, filters, status, private file path, expiry, row count, failure reason, and audit metadata.

### 16.4 `notifications`

- `id UUID PRIMARY KEY`
- `recipient_staff_id UUID NOT NULL REFERENCES staff_users(id)`
- `notification_type VARCHAR(64) NOT NULL`
- `title VARCHAR(180) NOT NULL`
- `body TEXT NULL`
- `record_type VARCHAR(64) NULL`
- `record_id UUID NULL`
- `read_at TIMESTAMPTZ NULL`
- `created_at TIMESTAMPTZ NOT NULL`

### 16.5 `audit_events`

Append-oriented:

- actor ID
- action code
- target type
- target ID
- source
- request ID
- correlation ID
- safe metadata
- before summary
- after summary
- IP or user-agent metadata where justified
- timestamp

### 16.6 `outbox_events`

- event type
- aggregate type and ID
- payload JSONB
- status
- available time
- attempts
- locked time
- completed time
- last error
- idempotency key

### 16.7 `job_records`

Stores job type, trigger, payload reference, status, attempts, retry time, timeout, correlation ID, user-visible progress, result, and failure metadata. These records track ARQ job execution durably in PostgreSQL — ARQ and Redis coordinate execution, but `job_records` remains the durable business truth.

## 17. INTEGRATIONS AND WEBHOOKS

### 17.1 `integration_connections`

Stores provider type, connection status, safe configuration metadata, credential reference, last successful check, last failure, and enabled state.

Never store raw secrets in ordinary application columns.

### 17.2 `webhook_events`

- `id UUID PRIMARY KEY`
- `provider VARCHAR(64) NOT NULL`
- `provider_event_id VARCHAR(200) NOT NULL`
- `event_type VARCHAR(120) NOT NULL`
- `received_at TIMESTAMPTZ NOT NULL`
- `signature_valid BOOLEAN NOT NULL`
- `processing_status VARCHAR(32) NOT NULL`
- `processed_at TIMESTAMPTZ NULL`
- `failure_reason TEXT NULL`
- `payload_hash VARCHAR(128) NULL`
- unique provider and provider event ID

### 17.3 `integration_sync_runs`

Stores provider, sync type, start, finish, status, counts, error summary, and cursor/checkpoint metadata.

## 18. DATABASE INDEXING REQUIREMENTS

Mandatory index review areas:

- all frequently joined foreign keys
- customer normalized phone and email
- customer status, segment, assigned staff, last order
- lead status, source, assignee, follow-up, created time
- order status, source, customer, payment status, fulfilment status, created time
- reservation date, status, customer, approval state
- conversation customer, lead, assigned staff, last message
- message conversation and created time
- provider message ID
- inventory stock status, expiry, storage zone
- stock movement item and occurred time
- notification recipient, read state, created time
- audit actor, target, action, created time
- campaign status and scheduled time
- outbox status and available time
- job status and retry time

Use partial indexes for active, unread, pending, non-deleted, and failed-but-retryable records when justified.

## 19. API FOUNDATIONS

### 19.1 Base path

Use `/api/v1`.

### 19.2 Authentication

Every protected endpoint requires a valid authenticated session or bearer token according to the final session architecture.

The backend must:

1. validate the token
2. load the internal staff user
3. reject disabled or suspended accounts
4. evaluate permission and record scope using the canonical capability registry (§4.4)
5. log sensitive actions

### 19.3 Standard response shapes

Single resource:

```json
{
  "data": {
    "id": "uuid",
    "...": "..."
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

Paginated resource:

```json
{
  "data": [],
  "pagination": {
    "next_cursor": null,
    "previous_cursor": null,
    "page": 1,
    "page_size": 25,
    "total": 0
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

Cursor and page fields should only appear where applicable.

### 19.4 Standard error shape

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request could not be processed.",
    "field_errors": {
      "email": ["Enter a valid email address."]
    },
    "request_id": "uuid"
  }
}
```

Stable error categories:

- `validation_error`
- `authentication_required`
- `permission_denied`
- `not_found`
- `conflict`
- `invalid_state_transition`
- `rate_limited`
- `external_dependency_unavailable`
- `integration_configuration_error`
- `retryable_processing_failure`
- `internal_error`

### 19.5 Pagination

- Default page size: 25.
- Maximum ordinary page size: 100.
- High-volume feeds should use cursor pagination.
- Offset pagination may be used for stable admin lists.
- No endpoint may return an unbounded collection.

Cursor pagination is preferred for:

- messages
- activity feeds
- audit events
- notifications
- stock movements
- order status history
- realtime-sensitive feeds

### 19.6 Filtering and sorting

Every list endpoint must use explicit filter and sort allowlists.

Reject unknown sort columns and unsafe arbitrary expressions.

### 19.7 Search

- Normalize phone and email searches.
- Use PostgreSQL full-text search where appropriate.
- Use trigram indexes only when justified.
- Debounce frontend search requests.
- Enforce minimum query lengths where useful.
- Never fetch all rows and filter in the browser.

### 19.8 Idempotency

Require `Idempotency-Key` for operations such as:

- order creation
- payment confirmation handling
- refund creation
- loyalty award creation
- campaign launch
- export creation
- provider webhook processing
- inventory reservation

Store the key, request fingerprint, response reference, and expiry policy.

### 19.9 Concurrency

Use optimistic version checks or transactional locks for:

- customer merges
- order transitions
- inventory adjustments
- stock reservation and consumption
- reservation approval and capacity
- loyalty redemption
- integration settings

Return `409 Conflict` when the client edits stale data.

## 20. AUTH AND USER API

### 20.1 Current user

`GET /api/v1/auth/me`

Returns:

- staff profile
- roles
- permissions
- scopes
- department
- account status
- feature availability

### 20.2 Staff administration

- `GET /api/v1/staff-users`
- `POST /api/v1/staff-users/invitations`
- `GET /api/v1/staff-users/{id}`
- `PATCH /api/v1/staff-users/{id}`
- `POST /api/v1/staff-users/{id}/roles`
- `DELETE /api/v1/staff-users/{id}/roles/{role_id}`
- `POST /api/v1/staff-users/{id}/disable`
- `POST /api/v1/staff-users/{id}/enable`

Every role or status change is audited.

## 21. RESTAURANT SETTINGS API

- `GET /api/v1/settings/restaurant`
- `PATCH /api/v1/settings/restaurant`
- `GET /api/v1/settings/operating-hours`
- `PUT /api/v1/settings/operating-hours`
- `GET /api/v1/settings/report-recipients`
- `PUT /api/v1/settings/report-recipients`
- `GET /api/v1/settings/notifications`
- `PUT /api/v1/settings/notifications`

Sensitive setting changes require explicit permissions (`settings.manage`, `settings.integrations.update`) and audit logs.

## 22. CUSTOMER API

### 22.1 Endpoints

- `GET /api/v1/customers`
- `POST /api/v1/customers`
- `GET /api/v1/customers/{customer_id}`
- `PATCH /api/v1/customers/{customer_id}`
- `DELETE /api/v1/customers/{customer_id}` soft delete
- `POST /api/v1/customers/{customer_id}/restore`
- `GET /api/v1/customers/{customer_id}/timeline`
- `GET /api/v1/customers/{customer_id}/orders`
- `GET /api/v1/customers/{customer_id}/reservations`
- `GET /api/v1/customers/{customer_id}/communications`
- `GET /api/v1/customers/{customer_id}/feedback`
- `GET /api/v1/customers/{customer_id}/loyalty`
- `POST /api/v1/customers/{customer_id}/notes`
- `POST /api/v1/customers/{customer_id}/tags`
- `DELETE /api/v1/customers/{customer_id}/tags/{tag_id}`
- `POST /api/v1/customers/merge`
- `GET /api/v1/customers/duplicates`
- `PUT /api/v1/customers/{customer_id}/consents/{consent_type}`

### 22.2 Customer list filters

- search
- customer type
- status
- segment
- assigned staff
- dietary preference
- last order date range
- minimum lifetime value
- loyalty enrollment
- deleted state

### 22.3 Example customer seed

Development fixtures may use:

- Ananya Rao — vegetarian — 12 completed orders — favorite Paneer Tikka Pizza — 680 loyalty points
- Rahul Mehta — non-vegetarian — 8 completed orders — favorite Double Crunch Chicken Burger — at-risk
- Shreya Kulkarni — Jain preference — 5 completed orders — favorite Jain Aloo Crunch Burger
- BrightWave Technologies — corporate customer — monthly lunch orders — assigned to Nikhil Jain

These examples must remain clearly marked as dummy data.

## 23. LEAD API

- `GET /api/v1/leads`
- `POST /api/v1/leads`
- `GET /api/v1/leads/{lead_id}`
- `PATCH /api/v1/leads/{lead_id}`
- `DELETE /api/v1/leads/{lead_id}` soft delete
- `POST /api/v1/leads/{lead_id}/assign`
- `POST /api/v1/leads/{lead_id}/transition`
- `POST /api/v1/leads/{lead_id}/activities`
- `POST /api/v1/leads/{lead_id}/follow-ups`
- `PATCH /api/v1/leads/{lead_id}/follow-ups/{follow_up_id}`
- `POST /api/v1/leads/{lead_id}/convert`
- `GET /api/v1/leads/{lead_id}/timeline`

Transition endpoint requires:

- target status
- reason when required
- expected version

Dummy lead fixtures must match `PROJECT_PLAN.md`.

## 24. ORDER API

### 24.1 Endpoints

- `GET /api/v1/orders`
- `POST /api/v1/orders`
- `GET /api/v1/orders/{order_id}`
- `PATCH /api/v1/orders/{order_id}` for allowed pre-confirmation edits
- `POST /api/v1/orders/{order_id}/transition`
- `POST /api/v1/orders/{order_id}/cancel`
- `POST /api/v1/orders/{order_id}/refund-request`
- `GET /api/v1/orders/{order_id}/history`
- `GET /api/v1/orders/{order_id}/payments`
- `GET /api/v1/orders/{order_id}/inventory-reservations`

### 24.2 Create order rules

The backend must:

1. load current product and variant prices
2. validate availability
3. validate modifiers
4. calculate subtotal, tax, discounts, packaging, delivery, loyalty, and total (all in integer minor units)
5. ignore client-provided authoritative totals
6. create order and order item snapshots
7. reserve inventory at the configured state
8. create audit and outbox events

### 24.3 Status transition

`POST /api/v1/orders/{order_id}/transition`

Request:

```json
{
  "target_status": "preparing",
  "reason": null,
  "expected_version": 4
}
```

Invalid transitions return `409 invalid_state_transition`.

## 25. MENU AND INVENTORY API

### 25.1 Menu

- `GET /api/v1/menu/categories`
- `POST /api/v1/menu/categories`
- `PATCH /api/v1/menu/categories/{id}`
- `GET /api/v1/menu/products`
- `POST /api/v1/menu/products`
- `GET /api/v1/menu/products/{id}`
- `PATCH /api/v1/menu/products/{id}`
- `POST /api/v1/menu/products/{id}/availability-override`
- `GET /api/v1/menu/products/{id}/recipe`
- `PUT /api/v1/menu/products/{id}/recipe`
- `GET /api/v1/menu/modifiers`
- `POST /api/v1/menu/modifiers`

### 25.2 Inventory

- `GET /api/v1/inventory/items`
- `POST /api/v1/inventory/items`
- `GET /api/v1/inventory/items/{id}`
- `PATCH /api/v1/inventory/items/{id}`
- `GET /api/v1/inventory/items/{id}/movements`
- `POST /api/v1/inventory/items/{id}/adjustments`
- `POST /api/v1/inventory/receipts`
- `POST /api/v1/inventory/transfers`
- `POST /api/v1/inventory/waste`
- `POST /api/v1/inventory/cycle-counts`
- `GET /api/v1/inventory/alerts`
- `GET /api/v1/inventory/batches`
- `GET /api/v1/suppliers`
- `POST /api/v1/suppliers`
- `GET /api/v1/suppliers/{id}`
- `PATCH /api/v1/suppliers/{id}`

Every stock mutation requires permission (`inventory.adjust`, `inventory.receive`, `inventory.transfer`), reason where applicable, transaction safety, and an append-only movement record.

## 26. RESERVATION API

- `GET /api/v1/reservations`
- `POST /api/v1/reservations`
- `GET /api/v1/reservations/{id}`
- `PATCH /api/v1/reservations/{id}`
- `POST /api/v1/reservations/{id}/approve`
- `POST /api/v1/reservations/{id}/reject`
- `POST /api/v1/reservations/{id}/request-clarification`
- `POST /api/v1/reservations/{id}/assign-tables`
- `POST /api/v1/reservations/{id}/arrive`
- `POST /api/v1/reservations/{id}/seat`
- `POST /api/v1/reservations/{id}/complete`
- `POST /api/v1/reservations/{id}/no-show`
- `POST /api/v1/reservations/{id}/cancel`
- `GET /api/v1/reservations/capacity`
- `GET /api/v1/reservations/calendar`

Approval endpoint (`reservations.approve`) must check:

- operating hours
- requested time
- guest count
- seating capacity
- conflicting assignments
- large-group rules
- special requests

No automatic approval.

## 27. COMMUNICATION API

- `GET /api/v1/conversations`
- `POST /api/v1/conversations`
- `GET /api/v1/conversations/{id}`
- `PATCH /api/v1/conversations/{id}`
- `GET /api/v1/conversations/{id}/messages`
- `POST /api/v1/conversations/{id}/messages`
- `POST /api/v1/conversations/{id}/notes`
- `POST /api/v1/conversations/{id}/assign`
- `POST /api/v1/conversations/{id}/close`
- `POST /api/v1/conversations/{id}/reopen`
- `GET /api/v1/communication-templates`

Sending a message must:

1. validate permission
2. validate channel and provider configuration
3. validate consent where applicable
4. create durable outbound message record
5. enqueue delivery job (ARQ)
6. return queued status

## 28. KNOWLEDGE BASE API

- `GET /api/v1/knowledge/folders`
- `POST /api/v1/knowledge/folders`
- `PATCH /api/v1/knowledge/folders/{id}`
- `GET /api/v1/knowledge/documents`
- `POST /api/v1/knowledge/documents`
- `GET /api/v1/knowledge/documents/{id}`
- `PATCH /api/v1/knowledge/documents/{id}`
- `POST /api/v1/knowledge/documents/{id}/versions`
- `GET /api/v1/knowledge/documents/{id}/versions`
- `POST /api/v1/knowledge/documents/{id}/archive`
- `POST /api/v1/knowledge/documents/{id}/restore`
- `GET /api/v1/knowledge/search`

Uploads use a quarantine and scanning pipeline. Download URLs are short-lived and permission checked.

## 29. STAFF AND HR API

- `GET /api/v1/staff`
- `POST /api/v1/staff`
- `GET /api/v1/staff/{id}`
- `PATCH /api/v1/staff/{id}`
- `GET /api/v1/staff/{id}/documents`
- `POST /api/v1/staff/{id}/documents`
- `GET /api/v1/leave-requests`
- `POST /api/v1/leave-requests`
- `POST /api/v1/leave-requests/{id}/approve`
- `POST /api/v1/leave-requests/{id}/reject`
- `GET /api/v1/training-records`
- `POST /api/v1/training-records`
- `GET /api/v1/shifts`
- `POST /api/v1/shifts`

HR-sensitive fields require the dedicated `staff.hr_sensitive.read` permission and must not be included in ordinary staff list responses.

## 30. MARKETING, LOYALTY, FEEDBACK, AND COMPLAINT API

### 30.1 Loyalty

- `GET /api/v1/customers/{id}/loyalty`
- `POST /api/v1/customers/{id}/loyalty/adjustments`
- `POST /api/v1/orders/{id}/loyalty/redeem`
- `GET /api/v1/loyalty/ledger`

### 30.2 Campaigns

- `GET /api/v1/campaigns`
- `POST /api/v1/campaigns`
- `GET /api/v1/campaigns/{id}`
- `PATCH /api/v1/campaigns/{id}`
- `POST /api/v1/campaigns/{id}/audience-preview`
- `POST /api/v1/campaigns/{id}/schedule`
- `POST /api/v1/campaigns/{id}/launch`
- `POST /api/v1/campaigns/{id}/cancel`
- `GET /api/v1/campaigns/{id}/analytics`

### 30.3 Feedback and complaints

- `GET /api/v1/feedback`
- `POST /api/v1/feedback`
- `GET /api/v1/complaints`
- `POST /api/v1/complaints`
- `GET /api/v1/complaints/{id}`
- `PATCH /api/v1/complaints/{id}`
- `POST /api/v1/complaints/{id}/assign`
- `POST /api/v1/complaints/{id}/transition`
- `POST /api/v1/complaints/{id}/recovery-action`

## 31. REPORTING, EXPORT, NOTIFICATION, AND AUDIT API

### 31.1 Dashboard

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/orders`
- `GET /api/v1/dashboard/reservations`
- `GET /api/v1/dashboard/inventory-alerts`
- `GET /api/v1/dashboard/leads`
- `GET /api/v1/dashboard/customer-metrics`

Endpoints return pre-aggregated bounded data.

### 31.2 Reports

- `GET /api/v1/reports`
- `POST /api/v1/reports/generate`
- `GET /api/v1/reports/{id}`
- `GET /api/v1/report-schedules`
- `POST /api/v1/report-schedules`
- `PATCH /api/v1/report-schedules/{id}`
- `DELETE /api/v1/report-schedules/{id}`

### 31.3 Exports

- `POST /api/v1/exports`
- `GET /api/v1/exports/{id}`
- `GET /api/v1/exports/{id}/download`

Large exports are asynchronous.

### 31.4 Notifications

- `GET /api/v1/notifications`
- `POST /api/v1/notifications/{id}/read`
- `POST /api/v1/notifications/read-all`

### 31.5 Audit logs

- `GET /api/v1/audit-events`
- `GET /api/v1/audit-events/{id}`

Audit logs are read-only through ordinary application APIs, requiring the `audit.view` permission.

## 32. INTEGRATION API

- `GET /api/v1/integrations`
- `GET /api/v1/integrations/{provider}`
- `PATCH /api/v1/integrations/{provider}`
- `POST /api/v1/integrations/{provider}/test`
- `POST /api/v1/integrations/{provider}/disconnect`
- `GET /api/v1/integrations/{provider}/sync-runs`

No integration may be shown as connected without a verified successful connection state.

## 33. WEBHOOK ENDPOINTS

Examples:

- `POST /api/v1/webhooks/whatsapp`
- `POST /api/v1/webhooks/email/{provider}`
- `POST /api/v1/webhooks/payments/{provider}`
- `POST /api/v1/webhooks/zomato`
- `POST /api/v1/webhooks/swiggy`

Every webhook must:

- verify signature
- reject oversized payloads
- enforce replay protection where supported
- store provider event ID
- deduplicate processing
- return quickly
- move heavy work to the worker
- redact secrets from logs

## 34. REALTIME EVENT CONTRACTS

Suggested event names:

- `order.created.v1`
- `order.status_changed.v1`
- `reservation.requested.v1`
- `reservation.status_changed.v1`
- `conversation.message_created.v1`
- `notification.created.v1`
- `inventory.stock_critical.v1`

Event payloads include:

- event ID
- version
- record type
- record ID
- timestamp
- minimal safe change summary
- correlation ID

Clients must re-fetch authoritative data through APIs after reconnect or uncertainty.

## 35. RATE LIMITING

Apply route-specific policies.

Examples:

- authentication routes: strict
- public reservation and order intake: moderate with abuse protection
- search endpoints: bounded per user
- exports and reports: low-frequency
- message sending: provider and user limits
- webhooks: signature-protected with provider-aware limits

Return `429 Too Many Requests` with safe retry metadata.

## 36. SECURITY REQUIREMENTS

- Backend authorization on every protected operation, using the canonical capability registry.
- No service-role credentials in browser code.
- No direct privileged database access from the dashboard.
- Secure cookies where selected by the final auth implementation.
- Narrow CORS allowlist.
- Strict request schemas.
- No raw ORM objects in responses.
- No SQL or stack trace leakage.
- File signature, MIME, extension, and size validation.
- Private storage buckets.
- Signed URLs only after authorization.
- Webhook signature verification.
- Sensitive export auditing.
- Secret redaction in logs.
- Protection against SQL injection, XSS, CSRF where applicable, IDOR, path traversal, mass assignment, unsafe redirects, and oversized requests.

## 37. MIGRATION STRATEGY

Each phase adds reviewed Alembic migrations.

Every migration must be tested:

- from a clean database
- from the latest previous migration state
- with seed data where relevant
- for rollback or forward-fix behavior
- for lock impact and data preservation

Do not use destructive schema changes without a staged plan.

Recommended expansion pattern:

1. add nullable column or new table
2. deploy compatible code
3. backfill safely
4. enforce constraint
5. remove old path only after verification

## 38. SEED DATA RULES

Seed data must remain consistent with `PROJECT_PLAN.md`, including the canonical 65-person dummy staff set.

Allowed seed categories:

- RKPR dummy restaurant profile
- dummy staff names and roles
- dummy menu and prices
- dummy inventory quantities
- dummy suppliers
- dummy customer examples
- dummy lead examples
- dummy report recipients

Seed data must not contain:

- real credentials
- real provider IDs
- fake production API keys
- fabricated integration support
- fake connected-state records
- unapproved technology decisions

Production onboarding must use a controlled replacement or import process.

## 39. PERFORMANCE RULES

- Every list endpoint is paginated.
- Every common filter has a matching index review.
- No full customer, order, message, or audit dataset is loaded into the browser.
- No N+1 queries.
- Select only required columns.
- Use database-side aggregation.
- Use cursor pagination for deep high-volume feeds.
- Use background jobs (ARQ) for reports, exports, campaigns, files, AI, and reconciliation.
- Use short transactions.
- Keep realtime subscriptions scoped.
- Use caching only for measured expensive repeated queries.
- Never cache one user's sensitive response under another user's key.

## 40. API ACCEPTANCE CHECKLIST

The database and API layer is complete only when:

- schema migrations succeed from a clean database
- all foreign keys and constraints are active
- large collection endpoints are bounded
- indexes support common query patterns
- permission checks are backend enforced using the canonical capability registry
- invalid state transitions are rejected
- financial calculations are backend authoritative and stored as integer minor units
- duplicate webhook events are idempotent
- order and inventory writes are transaction-safe
- reservation approval remains human-controlled
- loyalty uses an append-only ledger
- audit events are created for sensitive operations
- exports and reports are asynchronous
- file access is private and permission checked
- error responses use stable codes
- OpenAPI documentation matches implementation
- dummy data remains isolated from production data
- no multi-tenant fields or architecture are introduced
- no RAG, embeddings, or pgvector tables are introduced

## 41. FINAL DATABASE AND API COMMAND

Implement the RKPR Restaurant CRM database and API as a secure, high-speed, single-business system. Keep PostgreSQL authoritative, business rules in FastAPI, collections bounded, writes transactional, financial logic precise (integer minor units, never floating point), status transitions explicit, permissions server-side using the single canonical capability registry, files private, integrations verified, jobs idempotent, and all sensitive operations auditable. Preserve the exact approved dummy dataset only for development and testing, while keeping real technical decisions, providers, libraries, security controls, and architecture strictly non-dummy and consistent across all project documents.
