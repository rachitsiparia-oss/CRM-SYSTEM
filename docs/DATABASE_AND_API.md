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

### 7.5 Phase 5 implementation notes and deviations

Recorded per CLAUDE.md section 1.1/27 ("when a change affects multiple documents, update all affected documentation"). None of these reopen a settled decision — they resolve gaps or forward-references this document left for a phase that hadn't landed yet.

- **`customer_preferences.favorite_product_id`** → the `products` table does not exist until Phase 6, so Phase 5 added `favorite_product_note VARCHAR(200) NULL` (free text) instead. Phase 6 should add the real `favorite_product_id UUID REFERENCES products(id)` column *alongside* `favorite_product_note`, not instead of it — staff may have already recorded a free-text favorite that doesn't match any catalogue item exactly.
- **`leads.campaign_id`** → the `campaigns` table does not exist until Phase 12, so Phase 5 added `campaign_reference VARCHAR(200) NULL` (free text) instead. Phase 12 should add the real FK alongside this column for the same reason as above.
- **`leads.status` allowed values** — this document's 10-value list (`new`/`contacted`/`qualified`/`interested`/`follow_up_scheduled`/`proposal_shared`/`negotiating`/`won`/`lost`/`closed`) is the one implemented; it is the canonical list. `won` is reachable only through `POST /api/v1/leads/{id}/convert`, never through `POST /api/v1/leads/{id}/transition` — the transition endpoint's allowed-transitions table has no path to `won` from any status.
- **`leads.do_not_contact`** — added as a `BOOLEAN NOT NULL DEFAULT FALSE` column, not a status value. It coexists with any pipeline status rather than replacing one, and blocks `POST /leads/{id}/follow-ups` (not other lead actions) when true.
- **Additional `leads` columns beyond this section's list**, all added during Phase 5 implementation: `last_contact_at TIMESTAMPTZ NULL` (set by logging a call/email/whatsapp/meeting activity), `qualification_notes TEXT NULL`, `food_preferences TEXT NULL`, `budget_notes TEXT NULL`, `converted_at TIMESTAMPTZ NULL`, `converted_by UUID NULL REFERENCES staff_users(id)`, `conversion_idempotency_key VARCHAR(160) NULL` (partial unique index, `WHERE conversion_idempotency_key IS NOT NULL` — makes `POST /leads/{id}/convert` safe to retry).
- **`customer_notes` and `lead_activities`/`lead_follow_ups` edit/soft-delete columns** — `customer_notes` gained `updated_at`/`updated_by`/`deleted_at`/`deleted_by` beyond this section's list, per `CORE_CRM_MODULES.md` §4.14's requirement that notes support editing and soft deletion rather than silent overwrite/delete. `lead_follow_ups` gained `purpose TEXT NULL`, `channel VARCHAR(32) NULL`, `completed_by UUID NULL REFERENCES staff_users(id)` per `CORE_CRM_MODULES.md` §5.10.
- **Customer archive mechanism** — `customers.customer_status` gained two lifecycle values beyond the documented set: `archived` (toggled by `DELETE`/`POST .../restore`) and `merged` (set once, by the merge workflow, alongside the new `merged_into_customer_id UUID NULL REFERENCES customers(id)` fast pointer). `SoftDeleteMixin`'s `deleted_at` remains available on the table but is not driven by these actions — this follows the same pattern `staff_users.account_status` already established in Phase 3.
- **Lead archive mechanism** — leads use `SoftDeleteMixin.deleted_at` directly (`DELETE /leads/{id}` sets it, `POST /leads/{id}/restore` clears it), unlike customers. Both are documented, intentional choices for their respective entities, not an inconsistency to reconcile.
- **`customer_consents`** — implemented as "one current row per `(customer_id, consent_type)`" via a unique constraint (the simpler of the two options this section itself offers), not append-only history. `granted_at`/`withdrawn_at` track that current row's own transition times.
- **Domain events** — Phase 5 records exactly five outbox event types via `app/outbox/service.py::record_domain_event`: `customer.created`, `customer.updated`, `customer.merged`, `lead.created`, `lead.stage_changed` (the last covers both ordinary transitions and conversion-to-`won`). No consumer/dispatcher exists yet — these are recorded for the documented future automation contract, per `INTEGRATIONS_AUTOMATIONS_REALTIME.md` §8.1, not read by anything today.
- **Row Level Security** — all 12 tables this phase created have RLS enabled in the same migration that creates them (`523aed98ebd1_add_phase5_customers_and_leads.py`), per the convention `SECURITY_PERFORMANCE_AND_QUALITY.md` §8.5 established in Phase 3: Supabase's PostgREST layer is reachable via the public anon key unless RLS blocks it, even though `apps/api`'s own connection (table-owning role) is unaffected.

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

### 8.7 Phase 6 implementation notes and deviations

Recorded per CLAUDE.md section 1.1/27, following the same convention section 7.5 established for Phase 5.

- **`products.food_type`** stays a binary `vegetarian`/`non_vegetarian` classification. `is_jain_capable`/`is_vegan_capable` (already documented) describe whether a product *can* be prepared that way, not a third base type.
- **Allergen/composition booleans** — `contains_egg`, `contains_dairy`, `contains_gluten`, `contains_nuts`, `contains_soy` (from `CORE_CRM_MODULES.md` §7.12) and `contains_alcohol` (this phase's own request) were added as a closed set of booleans, not a free-form tag list — CLAUDE.md section 5.3 forbids unbounded JSON blobs for core searchable business data.
- **`spice_level`** (`mild`/`medium`/`hot`/`extra_hot`) — not enumerated by any canonical document; added following the same pattern `customers.spice_preference` established in Phase 5.
- **Additional `products` columns beyond section 8.2's list**, all from this phase's own explicit feature list: `barcode VARCHAR(64) UNIQUE NULL` (placeholder, not validated against any real barcode format or scanner), `display_name VARCHAR(180) NULL` (customer-facing name when it should differ from the internal `name`), `short_description VARCHAR(240) NULL`, `dine_in_available`/`takeaway_available`/`delivery_available BOOLEAN NOT NULL DEFAULT TRUE` (per-channel availability — no real ordering channel exists until Phase 7, so these are staff-configured in advance), `sort_order INTEGER NOT NULL DEFAULT 0`, `is_featured`/`is_chef_recommended BOOLEAN NOT NULL DEFAULT FALSE`.
- **`product_images`** — not its own table in section 8.2 (which only has a single `image_storage_path` column on `products`). Added for this phase's own "image gallery" requirement and `CORE_CRM_MODULES.md` §7.11. `products.image_storage_path` stays the documented column, kept in sync by `app/menu/service.py` with whichever `product_images` row has `is_thumbnail = TRUE`, so existing call sites that only need "the one image" never need to know the gallery table exists. Image deletion is a hard delete, not soft — a removed gallery photo is not a record CLAUDE.md section 7 requires preserving.
- **`product_variants.is_available`/`.preparation_minutes`** — beyond section 8.3's list, per this phase's own request for "own availability" and "own preparation time (optional)" per variant. `is_available` mirrors the same active-vs-available split `products` already has; `preparation_minutes` overrides the parent product's prep time only when set, otherwise inherits.
- **`modifier_groups.sort_order`** — beyond section 8.4's list, per this phase's own "display order" requirement.
- **`modifiers.default_price_minor`** is the price used unless `modifier_group_items.price_minor_override` (also beyond section 8.5/8.6's explicit column lists) overrides it for a specific group mapping. Channel-specific pricing (mentioned in section 8.6 as optional) is deferred — no ordering channel exists until Phase 7.
- **Combos** (`PROJECT_PLAN.md` §7.8) are seeded as ordinary `products` rows in a "Combos" category with included items listed in `description` — no `combo_items` relational table is documented anywhere in this section, so a combo is not modeled as a bundle of other products this phase.
- **Nested categories and category images** — both mentioned conditionally in this phase's own instruction ("support nested categories if already described in documentation," "image (if approved)") but neither is described or approved anywhere in this document or `CORE_CRM_MODULES.md`, so neither was added. `menu_categories` stays flat with no image column.
- **Recipes, costing/margin, and menu analytics** (`CORE_CRM_MODULES.md` §7.9, §7.10, §7.15) are out of scope for Phase 6 — this phase's own instruction explicitly lists "recipes" and "analytics" under "DO NOT BUILD." Deferred to Phase 8 (Inventory) and Phase 11 (Reports) respectively.
- **Permissions** — `menu.manage` (a Phase 3 placeholder anticipating this phase) is replaced, not kept as an alias, by `menu.create`/`.update`/`.archive`/`.restore`/`.categories.manage`/`.modifiers.manage`/`.images.manage`, per this phase's own explicit instruction naming these exact codes and CLAUDE.md section 24's rule against a vague `.manage` catch-all once specific actions exist to gate instead.
- **Domain events** — Phase 6 records none. No menu/product events are documented anywhere in `INTEGRATIONS_AUTOMATIONS_REALTIME.md`, and CLAUDE.md forbids creating outbox events with no documented consumer.
- **Row Level Security** — all 8 tables this phase created have RLS enabled in the same migration that creates them (`b36e4b05396d_add_phase6_menu_and_product_management.py`), per the `SECURITY_PERFORMANCE_AND_QUALITY.md` §8.5 convention.
- **File storage** — product images are stored in a private Supabase Storage bucket (`menu-images`, created idempotently on first use since Storage buckets aren't provisioned by an Alembic migration), accessed only via short-lived signed URLs generated after a backend permission check, per TOOLS.md §5.3 and `SECURITY_PERFORMANCE_AND_QUALITY.md` section 9.5. Malware scanning (section 9.3's quarantine/scan/clean flow) is not implemented — no scanning provider is approved anywhere in `TOOLS.md`; file-signature verification via real image decode (Pillow) is implemented and is a different, real control.

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

### 9.8 Phase 8 implementation notes and deviations

Phase 8's own explicit instruction gave a 15-area functional scope (units, categories, locations, suppliers, items, batches, movements, balances, receipts, adjustments, wastage, transfers, stock counts, recipes, order integration) with its own non-negotiable ledger invariants and an explicit DO-NOT-BUILD list (no purchase orders, no supplier-invoice accounting, no multi-branch). Per `CLAUDE.md` §1.1, that instruction governs this deliverable's actual schema wherever it differs from §9.1–§9.7 above; every deviation actually shipped is recorded here.

**19 tables, not the 7 named in §9.1–§9.6** (`units_of_measure`, `inventory_categories`, `storage_locations`, `suppliers`, `inventory_items`, `inventory_batches`, `stock_movements`, `stock_balances`, `stock_receipts`, `stock_receipt_items`, `stock_adjustments`, `wastage_records`, `stock_transfers`, `stock_transfer_items`, `stock_counts`, `stock_count_lines`, `recipes`, `recipe_items`, `order_inventory_state`), all with RLS enabled, in one migration (`b34d3dac8a82_add_phase8_inventory_recipes_and_stock_`).

**`category`/`storage_zone`/`unit_of_measure` normalized into managed tables** (`inventory_categories`, `storage_locations`, `units_of_measure`), not the bare VARCHAR columns §9.1 documents — a functional requirement of this phase, not a stylistic choice: exact-decimal unit conversion, per-location balances, transfers between named locations, and per-location stock counts all need a real record to reference. `units_of_measure.conversion_factor` is "how many base units is one of this unit" (`NUMERIC(20,8)`, always exact Decimal, never binary float — this phase's own instruction applied to quantities the same way `CLAUDE.md` §7 applies it to money); only same-`unit_type` conversions are permitted, with no density-based weight↔volume conversion invented. A packaging purchase unit whose ratio is not universal (a box of buns vs. a box of napkins) is handled by `inventory_items.purchase_conversion_factor`, an explicit per-item override — `app.inventory.units.convert_purchase_quantity` only consults it when the purchase and base units are genuinely different `unit_type`s or the item sets it explicitly; a same-`unit_type` pair with no override silently uses the units' own generic factor, so any item purchased in an ambiguous packaging unit **must** set the override.

**`stock_movements` is the sole source of truth, append-only at two levels**: application code writes it only through `app.inventory.ledger.post_movement`/`reverse_movement`, and a database trigger (`rkpr_stock_movements_append_only()`) independently rejects any `DELETE` and restricts `UPDATE` to `reversed_by_movement_id`/`reversed_at` only. Sign convention: `quantity_delta` is signed and always in the item's base unit — positive adds to on-hand, negative removes. `order_reservation`/`reservation_release` are the sole exception: positive magnitude, `affects_on_hand = FALSE`, moving quantity between `stock_balances.reserved_quantity` and implicit "available" on the same row without ever touching on-hand — enforced by a CHECK constraint pairing `movement_type` with `affects_on_hand`, not just application discipline. `stock_balances` (§9.1's `current_stock`/`reserved_stock` become per-item/per-location/optional-batch rows here, plus all-location roll-up columns kept on `inventory_items` for the same two fields) is transactionally updated alongside every ledger post via row-level locking and is never an independent source of truth — `app.inventory.balances.verify_balances` recomputes it from the ledger and reports drift without auto-correcting; `rebuild_balances` is the separate, permission-gated (`inventory.balances.rebuild`), audited correction path.

**`inventory_items.stock_status`** is derived automatically from `current_stock` against `reorder_level` (`out_of_stock` at zero, `critical_stock` at or below half the reorder level, `low_stock` at or below the reorder level, otherwise `in_stock`) every time the ledger roll-up recomputes — but only when the item's *current* status is one of those four; the six operator-set states (`quarantined`/`expired`/`damaged`/`under_count_review`/`discontinued`, plus `reserved` which this phase deliberately never assigns automatically since reserved quantity is already precise on `stock_balances`) are never overwritten by the derivation pass. This automatic derivation was missing from the first implementation pass — caught only once the seed script was run against a live database and every item stayed `in_stock` regardless of quantity — and was added to both `refresh_item_rollup` and `rebuild_balances` before Phase 8 was considered complete.

**Batch `remaining_quantity` and `stock_balances` rows are ledger projections, initialized at zero, never pre-filled with the posted amount** — a real bug caught the same way: `receipts.post_receipt` and `transfers.post_transfer` originally created a freshly-received/transferred-in batch with `remaining_quantity` pre-set to the received/transferred quantity, and then the immediately-following `ledger.post_movement` call added the same quantity again on top, silently doubling every batch's stock on first receipt. Fixed by starting every new batch at zero and letting the ledger post be its sole writer, exactly like `stock_balances`.

**Adjustment and wastage records generate their id before posting the movement**, passing it directly as the movement's `reference_id` — not "post the movement, then update `reference_id` once the parent row exists," which the append-only trigger correctly rejects as an illegal post-facto edit. Receipts and transfers avoid this because their line rows (and therefore `reference_id`) already exist before the movement posts.

**Costing policy** (§9.1's `average_unit_cost_minor` exists but this phase does not implement weighted-average costing — the column is reserved for a later phase): each ingredient's cost basis is `standard_cost_minor`, falling back to `latest_purchase_cost_minor` when no standard cost is set; nothing computes or reads a running weighted average, since doing so without being asked would be "inventing complex accounting behavior" this phase's own instruction forbids. Per-ingredient `waste_factor` inflates required quantity (`effective_quantity = base_quantity / (1 − waste_factor)`); the recipe's own `preparation_loss_percentage` reduces usable yield (`effective_yield = yield_quantity × (1 − loss% / 100)`); `cost_per_yield_minor = round(total_ingredient_cost_minor / effective_yield)`, rounded ROUND_HALF_UP on the final integer minor-unit figure only.

**Recipe resolution policy** (§9.4/§9.5 as documented, with one explicit decision this phase's instruction left open): an exact `(product_id, variant_id)` match wins; otherwise the product's base recipe (`variant_id IS NULL`) applies; only a recipe whose `[effective_from, effective_to)` window contains the query instant is considered. No partial inheritance between a variant recipe and its base recipe exists — a variant either has its own complete recipe or uses the base recipe outright, per this phase's own fallback guidance ("if the documentation does not define inheritance, use one explicit resolved recipe... and document the decision").

**Order-to-inventory integration is a wrapper, not a modification of Phase 7's state machine.** `app.inventory.order_integration.transition_order_with_inventory` calls the unmodified `app.orders.service.transition_order` with inventory side effects sequenced around it: reservation happens *before* the transition call for `confirmed` (so `InsufficientStockError` aborts before the order status ever changes), consumption and release happen *after* for `preparing`/`cancelled`. No canonical document defines an order-to-inventory lifecycle, so this phase's own conservative default governs, recorded here per its own instruction: `confirmed` → reserve (rejects with a clear stock-shortage error if any tracked ingredient cannot be reserved, no override policy); `preparing` → consume (releases the matching reservation and deducts on-hand in the same operation, replaying the exact batch allocation snapshotted at reservation time rather than re-resolving the recipe, so consumption can never draw from a different batch than what was reserved); cancellation before consumption → release, no on-hand change; cancellation after consumption → stock is **not** automatically restored (`post_consumption_note` records that a human decision — a positive adjustment if recoverable, or wastage otherwise — is outstanding); `completed` → no inventory effect, consumption already happened at `preparing`. Idempotency: `order_inventory_state` (unique per order, states `pending`/`reserved`/`consumed`/`released`/`skipped`) makes every function a no-op once the state already reflects the requested outcome, and every individual ledger post additionally carries a deterministic `idempotency_key` (e.g. `order-reserve-{order_id}-{item_id}-{location_id}`). A product with no active resolved recipe is treated as not inventory-tracked and its order lines are silently skipped, not errored — no `is_inventory_tracked` flag exists on `Product` (Phase 6 scope), so recipe presence is that flag. Phase 7's actual transition table only allows `cancelled` from `pending_confirmation`/`preparing`/`ready`, never from `confirmed`, so "cancel while reserved but not yet consumed" is reachable today only from `pending_confirmation` (where nothing was ever reserved) — the branch is still implemented unconditionally and correctly, both because the instruction requires it and because a future phase could widen the transition table.

**Batch allocation is FEFO for expiry-tracked items, oldest-received-first otherwise** (`app.inventory.allocation.allocate_batches`, ordering active batches by `(expires_at IS NULL, expires_at ASC, received_at ASC)`), raising rather than silently substituting when an expired batch would need to be drawn from or when active non-expired batches don't sum to enough.

**Negative stock is refused by default**; `storage_locations.allows_negative_stock` (default `FALSE`, expected to stay `FALSE` per this phase's own instruction — "only if explicitly approved") is the sole, per-location, audited override. Reserved quantity must never exceed on-hand after a decrease unless that same flag is set.

**No purchase-order tables (§9.7's `purchase_orders`/`purchase_order_items`)** — `stock_receipts` are standalone, matching this phase's own 15-area scope (which omits purchase orders) and its explicit "do not build... procurement approval finance workflows" instruction. No supplier-invoice, accounts-payable, or accounting-journal tables exist for the same reason; `suppliers.payment_terms` is free descriptive text, not a posting rule.

**Permissions:** replaces the Phase 3 placeholder inventory permission set with 26 explicit codes (`inventory.view`, `.cost.view`, `.units.manage`, `.categories.manage`, `.locations.manage`, `.suppliers.manage`, `.items.create/.update/.archive/.restore`, `.receipts.create/.post/.reverse`, `.adjustments.create/.approve`, `.wastage.create/.approve`, `.transfers.create/.post/.reverse`, `.counts.create/.submit/.approve`, `.recipes.view/.manage`, `.balances.rebuild`), splitting "do the work" from "approve the work" so day-to-day data entry and sensitive approval/rebuild authority are independently grantable.

**Seed supplier deviation:** `PROJECT_PLAN.md` §9 documents exactly eight suppliers in full; several `PROJECT_PLAN.md` §8.2 catalogue rows name a supplier outside that list ("In-house production", "GreenGrain Foods", "FreshForm Foods", "Metro Grain Traders", "Metro Oil Traders", "Beverage Partner Demo", "ClearSpring Beverages", "SweetLine Desserts"). Rather than fabricating supplier records the canonical directory does not define (`CLAUDE.md` §16 / §24), `preferred_supplier_id` is left unset for those items.

**Manual verification checklist (authenticated workflows, for when a test Supabase session/`storageState` fixture exists):** this project has never had authenticated Playwright coverage (Phases 5, 6, 7, and 8 all stopped at the unauthenticated-redirect boundary for the same reason — no test Supabase session). Until that infrastructure exists, verify the following by hand with a real `owner`-or-equivalent staff account against a non-production environment:

1. Sign in and confirm "Menu, Products & Inventory" appears in the sidebar with the nine new Inventory children.
2. `/inventory` — dashboard KPI cards render real, non-zero numbers matching the seeded data (41 active items, 1 critical, 1 out-of-stock, 1 batch expiring within 7 days).
3. `/inventory/items` — create an item, confirm it appears in the list; open its detail page and confirm all four tabs (Overview, Stock by Location, Batches, Movements) render without error.
4. `/inventory/suppliers` — create a supplier, edit it, archive it, restore it.
5. `/inventory/receipts` — create a draft receipt, add a line for a non-batch-tracked item, post it, confirm the item's on-hand quantity increased on its detail page's Movements tab; create a second receipt for a batch-tracked item and confirm a batch appears on the Batches tab with the entered expiry date.
6. Reverse a posted receipt and confirm the on-hand quantity returns to its prior value and the receipt becomes read-only.
7. `/inventory/adjustments` — post a decrease adjustment and confirm the item's stock status updates accordingly (e.g. crosses into `low_stock`).
8. `/inventory/adjustments` (Wastage tab) — record wastage and confirm a negative movement appears in `/inventory/movements` filtered to that item.
9. `/inventory/transfers` — create a transfer between two locations, add a line, post it, confirm both the source and destination balances update on the item's Stock by Location tab.
10. `/inventory/stock-counts` — start a count for a location, enter a counted quantity different from the system quantity for at least one line, submit, approve, and confirm a `stock_count_adjustment` movement appears with the correct variance.
11. `/inventory/recipes` — create a recipe for a seeded menu product, add an ingredient, confirm the cost tab shows a computed cost and gross margin (or a clear "missing cost" message if the ingredient has no cost set).
12. Place a real order (Phase 7) for a product with an active recipe; confirm ingredient stock is reserved on `confirmed`, consumed on `preparing` (reservation released, on-hand deducted by the exact recipe quantity), and unaffected by `completed`.
13. Cancel an order at `pending_confirmation` (before any reservation exists) and confirm no stock movement is created.
14. Sign in as a role without `inventory.adjustments.approve` (e.g. `inventory_manager`) and confirm the balance-rebuild action at `/inventory/balances/rebuild` returns 403 (there is no dedicated rebuild page; verify via the API directly or a future admin surface).
15. Attempt to edit a posted receipt or transfer via the API directly and confirm it is rejected (`AlreadyPostedError` / 409-class response) — posted records must stay read-only in the UI as well.

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

### 10.7 Phase 7 implementation notes and deviations

Phase 7's own explicit instruction scoped this phase to the CRM side of orders only — no payment gateway integration, no kitchen-display/preparation-stage workflow, no inventory deduction, no delivery-partner tracking, no realtime — and gave its own exact status/source/type/table lists. Those lists differ from §10.1–§10.6 above; per `CLAUDE.md` §1.1 ("a document does not override... unless the user explicitly approves the change"), the phase's own explicit instruction governs this deliverable's actual schema, since implementing the fuller lifecycle documented above would require building the capabilities this exact phase forbids. §10.1–§10.6 remain the target for when payment-gateway integration (a later phase), real POS/Zomato/Swiggy import, delivery-partner tracking, and inventory reservation actually land; this section records every deviation the implementation actually shipped with.

**Sources (8, not 9):** `pos`, `walk_in`, `website`, `whatsapp`, `phone_call`, `zomato`, `swiggy`, `manual` — this phase's own list, not §10.1's 9-value set. No `corporate`/`event` source exists as a distinct value (a corporate or event order is still placed through one of the 8 real sources).

**Order type (3, not part of §10.1's fulfilment model):** `dine_in`, `takeaway`, `delivery` — a dedicated `order_type` column, this phase's own explicit field.

**Status (7, not 16):** `draft`, `pending_confirmation`, `confirmed`, `preparing`, `ready`, `completed`, `cancelled`. No `pending_payment`/`payment_verification_pending` (no payment gateway to be pending on), no `quality_check` (no kitchen-display workflow), no `picked_up`/`out_for_delivery`/`delivered` (no delivery-partner tracking), no `refund_requested`/`refund_processing`/`refunded` as order statuses (refunds are tracked via `order_payments.status = 'refunded'` and the order's derived `payment_status`, not a separate status branch — this keeps refund state in one place instead of two). The allowed-transition table (`app/orders/states.py`) is this phase's own literal diagram: cancellation is reachable only from `pending_confirmation`, `preparing`, and `ready` — not from `draft` or `confirmed` — implemented exactly as given rather than widened with an assumed extra branch, since the instruction enumerated the alternative flows individually and precisely.

**No `fulfilment_status`, `delivery_address_id`, `currency_code`, or per-status timestamp columns** (`accepted_at`/`preparing_at`/`ready_at`/`picked_up_at`/`out_for_delivery_at`/`delivered_at`/`cancelled_at`) on `orders` — those model capabilities (fulfilment tracking, delivery, multi-currency) out of scope for this phase. `estimated_completion_time` (this phase's own field) is the one completion-facing timestamp that exists. `lead_id` (nullable FK to `leads`) was added — this phase's own explicit "Lead (optional)" field, not documented above.

**Money summary-plus-itemized-table pattern:** `orders.discount_minor`/`.tax_minor`/`.charges_minor` are running sums; `order_discounts`/`order_taxes`/`order_charges` hold the itemized lines that sum to them — the same pattern this phase's own instruction requests ("Only normalize where it actually improves the design"). `packaging_minor`/`delivery_minor`/`loyalty_discount_minor` as separate `orders` columns (§10.1) do not exist; packaging and delivery charges are itemized `order_charges` rows instead (`charge_type IN ('packaging', 'delivery', 'service', 'other')`), and there is no loyalty program yet (Phase 12) to discount against.

**`order_item_modifiers` (a 12th table, not named in this phase's 11-table list):** required to store each item's "Modifiers" field (this phase's own instruction) as normalized rows rather than an unbounded JSON blob (`CLAUDE.md` §5.3) — the same table §10.3 already documents, added here as a normalization judgment call this phase's instruction explicitly authorized. Snapshots `modifier_name_snapshot`/`price_minor_snapshot` so later menu edits never alter historical orders, mirroring `order_items`' own product/variant snapshot fields (§10.2's `product_name_snapshot`/`variant_name_snapshot`, without `recipe_version` or `special_instructions` — no recipe module exists yet, and the equivalent free-text field is `order_items.kitchen_note`).

**`order_items.status`** is `active`/`cancelled` (whether the line is still part of the order), not a kitchen-stage value — no kitchen-display/preparation-stage workflow exists yet (this phase's own "DO NOT BUILD" list).

**Payments (`order_payments`, not the four-table `payments`/`payment_events`/`refunds`/`refund_events` set in §10.5):** one table, "recording only" per this phase's own instruction — `method` (`cash`/`card`/`upi`/`online`), `status` (`pending`/`partial`/`paid`/`refunded`/`failed`), `reference` (a staff-entered identifier, never a gateway callback), `recorded_by`. No provider IDs or webhook event IDs exist to deduplicate, since no gateway is integrated. The order's own `payment_status` is derived server-side from the sum of `paid` payments against `grand_total_minor` whenever a payment is added or its status changes.

**No `order_source_metadata` 1:1 columns beyond `external_order_id`/`external_platform_reference`/`reconciliation_note`** — placeholders for a future real POS/Zomato/Swiggy import adapter to populate; no fabricated payload is stored (`CLAUDE.md` §16).

**No `inventory_reservations` (§10.6):** inventory deduction is explicitly out of scope for this phase.

**Permissions:** replaces the Phase 3 placeholder Orders permission set (`orders.transition`, `orders.cancel.request`/`.approve`, `orders.refund.request`/`.approve`, `orders.discount.apply`) with this phase's own explicit codes (`orders.view`/`.create`/`.update`/`.transition`/`.cancel`/`.complete`/`.assign`/`.payments.manage`/`.discount.override`/`.notes.manage`) — not kept as aliases, the same treatment Phase 6 gave `menu.manage`. There is no separate refund permission: refunds are recorded through `orders.payments.manage`, not a standalone approval workflow.

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

### 11.5 Phase 9 implementation notes and deviations

Phase 9's own explicit instruction gave a much larger functional scope (floor/table management, an availability and conflict-detection engine, an assignment engine, a waitlist, walk-in conversion, Customer-360 integration, business hours/holidays/policies, order linkage, and a dashboard) than §11.1–§11.4 sketch. Per `CLAUDE.md` §1.1, that instruction governs this deliverable's actual schema wherever it differs from what is documented above; every deviation actually shipped is recorded here.

**16 tables, not the 4 named in §11.1–§11.4** (`dining_areas`, `restaurant_tables`, `table_status_history`, `table_blocks`, `reservations`, `reservation_notes`, `reservation_status_history`, `reservation_table_assignments`, `reservation_tags`, `reservation_tag_links`, `reservation_timeline`, `reservation_waitlist`, `business_hours`, `holiday_calendar`, `reservation_policies`, `reservation_settings`), all with RLS enabled, in one migration (`385abc1d4309_add_phase9_reservations_tables_floor_`).

**`status`/`approval_status` collapsed into one `status` column carrying all 15 values** — §11.1 documents both a `status` and a separate `approval_status` defaulting to `pending_review`, which can drift out of sync with each other (nothing prevents `status='requested'` while `approval_status='approved'`, for example). `reservations.status` alone now carries the full lifecycle, including the four states §11.1's `approval_status` uniquely named (`pending_review`, `needs_clarification`, `approved`, `rejected`); a separate `approved_by`/`approved_at`/`rejected_by`/`rejected_at`/`rejection_reason` set of attribute columns (already present in §11.1) still records who made the decision and why. One added state, `expired`, covers a request nobody reviewed within the configured window (`ReservationSettings.pending_request_expiry_minutes`) — not in §11.1's list, added because the instruction's own review workflow has no other way to represent a request that timed out.

**`guest_count`/`seating_zone` renamed to `party_size`/`dining_area_id`** — `dining_area_id` is a real foreign key to the new `dining_areas` table (see below), not the free-text `seating_zone VARCHAR(64)` §11.1 documents, so a reservation's area preference can actually be validated and joined against real floor data.

**`dining_areas` is a new managed reference table, not documented in §5 or §11** — code/name/description/is_active/sort_order, soft-deletable, structurally identical to `MenuCategory`/`StorageLocation` from earlier phases. Required because §5.3's `restaurant_tables.seating_zone` (free text) cannot support "Floor Overview," "assign by area preference," or per-area dashboard utilization, all explicitly named by this phase's own instruction.

**`restaurant_tables` redesigned around `dining_area_id` and a self-referencing `merged_with_table_id`, not §5.3's `table_code`/`seating_zone`/`merge_group VARCHAR`** — adds `minimum_capacity`/`maximum_capacity` (capacity-fit matching for the assignment engine), `shape`, `status` (a live fast-pointer mirroring `Order.assigned_staff_id`'s pattern, with `table_status_history` as the append-only ledger), `is_wheelchair_accessible`, `is_temporary`, and `qr_identifier`. "Merged" and "Split" from this phase's own instruction are not both persistent states: a merged secondary table's `status='merged'` with `merged_with_table_id` pointing at the primary; "split" is the *action* that clears both, recorded as a `table_status_history` event, not a seventh status value. "Temporary" is `is_temporary`, a flag (an overflow table can independently be available/occupied/blocked), not a status.

**`table_blocks` is a new table, not documented anywhere in §5 or §11** — time-bounded holds (cleaning/maintenance/private-event/other) consulted by the availability engine alongside posted reservations; not soft-deletable, a block is either still active or has run its course, the same "closed, not deleted" treatment `StockCount`/`StockTransfer` gave a finished document in Phase 8.

**`business_hours` replaces §5.2's `operating_hours`**, dropping `service_type` (this phase's own instruction covers reservation-taking hours only, not menu service-period cutoffs like `last_dine_in_order_minutes_before_close` — that remains Orders/Menu territory) and adding `closes_next_day` (Friday/Saturday close after midnight per `PROJECT_PLAN.md` §3.3) and one optional break window. Unique per `day_of_week` alone (no `service_type` composite), so exactly seven rows exist at all times. `holiday_calendar` is new, layering date-specific full closures or special hours on top of the weekly schedule.

**`reservation_policies`/`reservation_settings` are new singleton tables** — a constant-valued unique `singleton_guard` boolean enforces at most one row of each. `reservation_policies` holds numeric business-rule thresholds this phase's own instruction names (deposit default, advance-booking limit, minimum notice, cancellation window, no-show grace, buffers, party-size bounds, the >18-guest large-party threshold `PROJECT_PLAN.md` §11.2 requires); `reservation_settings` holds feature toggles and timing for the engines (auto-assignment/waitlist/online-booking/walk-in enabled, default reservation duration, pending-request expiry, reminder lead time) — kept as two tables rather than one so "policy" (a business rule staff might change deliberately and rarely) and "settings" (operational toggles) stay independently permission-scoped and auditable.

**Walk-in approval bypass**: `PROJECT_PLAN.md` §11.2's "No automated approval is permitted" is satisfied for a walk-in by the staff member who creates and immediately seats the guest — `app.reservations.walkin.create_walk_in` creates the row already at `status='arrived'` with `approved_by` set to the acting staff member, never bypassing the human-approval rule, only skipping the asynchronous review queue that only makes sense for a future-dated booking.

**Customer-360 reservation statistics (visit frequency, no-show/cancellation counts, average party size, preferred area/table/time, last visit, lifetime visits) are computed by database-side aggregation at read time** (`app.reservations.customer_stats`), not stored as new `Customer` columns — Phase 5's shipped, tested `Customer` schema stays untouched, and the numbers are always exactly consistent with the reservation history itself. A future Loyalty phase consumes these same values through this same read path, not a duplicated column set.

**Order linkage is a thin FK pointer, not an order-creation path** — `reservations.order_id` is set once an order already exists (via the normal Orders module, Phase 7's own domain); `app.reservations.order_link` only records/clears the pointer. Reservation completion does not write anything into a separate "visit history" table — that history is exactly what the Customer-360 aggregation above already computes from completed reservations.

**Availability/conflict engine is timezone-aware end to end** (`app.reservations.availability`, `Asia/Kolkata`) — `Reservation.reservation_date`/`start_time`/`end_time` are the restaurant's own local wall-clock booking (matching `Order`'s existing "today" convention), while `TableBlock.starts_at`/`ends_at` are genuine `TIMESTAMPTZ` UTC instants; every window the engine builds is localized before comparison. A table currently `blocked`/`maintenance`/`merged` (live `status`) is excluded from every date's availability outright — an ad hoc block created via a direct status transition (rather than `create_table_block`) has no defined end time, so there is no way to know it clears before some future date; excluding it everywhere is the fail-closed choice `CLAUDE.md` §24 favors over risking a double booking. (A real timezone bug — comparing the naive local window directly against `TableBlock`'s tz-aware UTC window, which raises `TypeError` in Python and would otherwise silently mis-evaluate near the IST/UTC offset boundary — was caught by `tests/test_reservation_availability.py` and fixed before this phase was considered complete.)

**Reservation creation is idempotent** (`reservations.idempotency_key`, unique when set, mirroring `Order.idempotency_key`) — not named in §11.1, added per `CLAUDE.md` §7's "prevent duplicate ... reservations ... using ... idempotency."

**Permissions:** replaces the Phase 3 placeholder reservation permission set (`reservations.view/.create/.update/.approve/.transition`) with 13 explicit codes, keeping all five placeholders and adding `.cancel`, `.complete`, `.assign`, `.notes.manage`, `.tags.manage`, `.waitlist.manage`, `.tables.manage`, `.settings.manage` — splitting floor management, waitlist operation, and policy/hours configuration into independently grantable authority, the same "doing vs. approving vs. configuring" split Phase 8 applied to inventory.

**Not built in this phase (deferred, not hidden):** no reminder-dispatch job or WhatsApp/email adapter exists — `reminder_scheduled` is a real state in the lifecycle and `reservation_settings.reminder_lead_time_minutes` is a real, seeded configuration value, but nothing currently transitions a reservation into that state automatically or sends anything; the same is true of `confirmation_sending` → `confirmed` (both are real states any staff member can move a reservation through via the transition endpoint, but no automated message send is wired up). This is intentional: actual message dispatch is Communication Hub's own domain (§12, not yet built), and `CLAUDE.md` §14's "engine, not scheduler" principle means Phase 9 provides the deterministic state machine and configuration a future scheduled job can drive, not the job itself. `PROJECT_PLAN.md` §3.4's table counts do not sum to its own stated indoor/outdoor guest totals (72/20) — reproduced exactly as listed in seed data rather than adjusted to reconcile, the same deliberately unforced arithmetic gap Phase 8 recorded for its supplier catalogue.

**Manual verification checklist (authenticated workflows, for when a test Supabase session/`storageState` fixture exists):** this project has never had authenticated Playwright coverage (Phases 5 through 8 all stopped at the unauthenticated-redirect boundary for the same reason — no test Supabase session). Until that infrastructure exists, verify the following by hand with a real `owner`-or-equivalent staff account against a non-production environment:

1. Sign in and confirm "Reservations & Calendar" appears in the sidebar with its eight children.
2. `/reservations` — dashboard KPI cards render real numbers matching the seeded data (13 reservations, 2 arrived, 1 each completed/confirmed/seated/no-show/cancelled-by-customer/cancelled-by-restaurant/rejected/expired/pending-review/needs-clarification/requested).
3. `/reservations/list` — create a reservation, confirm it appears; open its detail page and step it through `pending_review` → Approve → `confirmation_sending` → `confirmed` → `arrived` → `seated` → `completed`, confirming each button set only offers valid next steps.
4. On a fresh `pending_review` reservation with no table created in its dining area, confirm Approve fails with a 409 "no table available" error; create a table in that area and confirm Approve then succeeds.
5. Reject a `pending_review` reservation without a reason and confirm it is refused; supply a reason and confirm it moves to `rejected`.
6. `/reservations/tables` — create a dining area and two tables in it; confirm both appear grouped under the area on the Tables & Floor page.
7. Open a table's detail page, merge it with another table, confirm the secondary table's status becomes `merged`; split them and confirm it returns to `available`.
8. Create a table block (e.g. `maintenance`), confirm the table's status updates and it disappears from `/reservations/availability` results for an overlapping window; release the block and confirm it reappears.
9. `/reservations/waitlist` — add a guest, confirm they appear; use "Seat now" and confirm it creates a walk-in reservation (status `arrived`) and marks the waitlist entry `promoted` with `promoted_reservation_id` set.
10. `/reservations/business-hours` — edit a day's hours, confirm the save persists; add a holiday and confirm a reservation request on that date is rejected by the availability check.
11. `/reservations/settings` — edit a policy value (e.g. `large_party_threshold`) and confirm creating a reservation just above the new threshold is rejected with the "handled as an event or bulk lead" message.
12. Sign in as a role without `reservations.approve` (e.g. `front_of_house_staff`) and confirm the Approve/Reject buttons are unavailable and the API returns 403 if called directly.
13. Sign in as a role without `reservations.tables.manage` and confirm dining-area/table creation is refused both in the UI and via a direct API call.

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

### 12.5 Phase 10 implementation notes and deviations

Phase 10's own explicit instruction gave a much larger functional scope than §12.1–§12.4 sketch — 23 numbered Communication Hub domains (unified conversations, message lifecycle, provider adapters, templates, consent/suppression, inbound/status webhooks, scheduling, business hours, analytics, and more), plus, per the user's own explicit choice after the instruction's scope was found to omit two of `PROJECT_PLAN.md`'s own Phase 10 scope bullets, the full Operational Tasks and Notifications Center scope in the same pass. Per `CLAUDE.md` §1.1, that combined instruction governs this deliverable's actual schema wherever it differs from what is documented above; every deviation actually shipped is recorded here.

**21 tables, not the 4 named in §12.1–§12.4** (`communication_channels`, `conversations`, `conversation_status_history`, `conversation_assignments`, `conversation_links`, `messages`, `message_delivery_attempts`, `message_status_history`, `message_attachments`, `message_templates`, `scheduled_messages`, `communication_preferences`, `communication_consents`, `communication_suppressions`, `inbound_webhook_events`, `provider_status_events`, `manual_call_logs`, `task_records`, `task_assignments`, `task_status_history`, `notifications`), all with RLS enabled, in one migration (`0ad5d0f1ece4_add_phase10_communication_hub_tasks_and_`). `notifications` replaces (not extends in a separate table) the sketch already at DATABASE_AND_API.md §16.4 — see below.

**`Message.delivery_status` carries both the outbound and inbound lifecycles the instruction itself documents separately** (outbound: `draft`/`queued`/`processing`/`sent`/`delivered`/`read`/`failed`/`cancelled`/`suppressed`; inbound: `received`/`processed`/`assigned`/`replied`/`resolved`/`spam`; internal notes: `created`) — the same collapse `Reservation.status` made of its own two documented columns in Phase 9. Which subset is valid for a given row is enforced by `app.communications.states`, keyed on `direction`, not by a second column; the transition graph itself is the "no regression on an out-of-order webhook" guarantee the instruction requires (`delivered` has no edge back to `queued`, `read` has no edge back to `delivered`, etc.).

**No stored `conversation_timeline_events` table** — the conversation timeline the instruction names is a read-time union over `messages` + `conversation_status_history` + `conversation_assignments` (`app.communications.service.get_conversation_timeline`), the same read-time-aggregation-over-existing-tables pattern Phase 9's Customer-360 reservation statistics established, rather than a fourth dual-written ledger.

**No `message_template_versions` table** — `MessageTemplate.version` (from the standard `AuditedMixin`) is optimistic concurrency only. A template edit does not need its own historical row because every message a template ever produced keeps its own rendered snapshot (`Message.body_text` + `Message.rendered_template_variables`), which is what the instruction's own auditability requirement ("store the rendered content actually sent") actually needs.

**`ConversationLink` is polymorphic** (`linked_type` IN `reservation`/`order`/`waitlist_entry`/`feedback_case`, `linked_id` with no FK) rather than a set of nullable FK columns on `Conversation` — a conversation can accumulate links to more than one order over its life (a repeat customer messaging about a second order in the same thread), which a single `order_id` column cannot represent. `TaskRecord.related_type`/`related_id` make the identical tradeoff for the same reason.

**`communication_channels` folds provider configuration into the channel row itself** — no separate `communication_provider_configs` table exists. Provider selection, sender identity, rate limits, template requirement, business-hours restriction, and a self-referencing `fallback_channel_id` are all columns on `communication_channels`; no provider secret is ever stored there (CLAUDE.md §16) — real credentials live only in environment configuration, referenced by a `provider_config_key` string.

**Operational Tasks recurrence is embedded, not a `task_recurrence_rules` table** — `TaskRecord.is_recurring_template`/`recurrence_rule` (JSONB: frequency/interval/days-of-week/end-date)/`parent_task_id`/`next_occurrence_generated_at` on the same table. A recurring task is a template row that `app.tasks.service.generate_due_recurring_tasks` reads and spawns dated instances from (each instance idempotency-keyed `{template_id}:{due_date}` so re-invoking the generator never double-spawns), which needs no independent lifecycle of its own.

**`notifications` extends, not replaces, the existing §16.4 sketch** — added `priority`, `dismissed_at`, `actioned_at`, and a `dedup_key` whose partial unique index is the DB-level enforcement of "avoid generating duplicate notifications for repeated events." No `notification_preferences` table was built in this phase — every staff member sees notifications relevant to their own assignments by default; per-user muting is deferred, not hidden.

**A real SQLAlchemy JSONB gotcha, caught by a model-constraint test and fixed**: SQLAlchemy's `JSON`/`JSONB` column type defaults to `none_as_null=False`, meaning a Python `None` assigned to a nullable JSONB column is stored as a JSON `null` *value*, not SQL `NULL` — so `recurrence_rule IS NOT NULL` was silently `TRUE` even for a non-recurring task, defeating the `recurring_template_requires_rule` CHECK constraint's protection for the one case it exists to catch (a recurring template created with no rule). Fixed by setting `JSONB(none_as_null=True)` on `TaskRecord.recurrence_rule`, `Message.rendered_template_variables`, and `ScheduledMessage.template_variables` — a Python-side SQLAlchemy behavior flag, not a DDL/migration change.

**A migration-generation tooling bug, caught by the seed script and fixed before this phase was considered complete**: the first pass at wrapping ruff's 100-character line limit for long multi-value `CHECK` constraint strings used a custom line-splitting script that dropped the separating `", "` at several line-wrap boundaries, silently merging two enum values into one malformed array element (e.g. `'web_chat''manual_call'` instead of `'web_chat', 'manual_call'`) in the generated migration — a real correctness bug that would have quietly narrowed several CHECK constraints' accepted value sets. Caught when seeding `communication_channels` raised `CheckViolation` for a legitimately-valid `web_chat` code. The migration was regenerated from a clean `alembic revision --autogenerate` and the still-too-long lines were resolved with trailing `# noqa: E501` comments instead of any further string manipulation.

**Provider abstraction ships with exactly one adapter, `InternalMockProvider`** — `app.communications.providers.ProviderAdapter` defines the stable capability surface (send text/template, parse inbound/status webhook, validate signature); no real WhatsApp Cloud API/Twilio/SendGrid adapter exists, matching `docs/TOOLS.md` §10's "final provider approval required" status and this project's own earlier env-var research (no provider chosen, no environment variable names locked in). Every seeded `communication_channels` row's `provider` is `internal_mock`. Registering a real provider later means adding one adapter class and a `provider` value on the channel row — no change to any caller of `send_text`/`parse_inbound_webhook`/etc.

**Permissions:** replaces the Phase 3 placeholder pair (`communications.view`/`.send`) with 21 explicit codes (not kept as aliases, the same treatment every prior phase gave its own Phase 3 placeholders), and adds 8 new `tasks.*` codes and 1 new `notifications.manage` code — none of which existed as placeholders anywhere.

**Not built in this phase (deferred, not hidden):** no automated recurring/timed invocation of `app.communications.scheduling.process_due_scheduled_messages` or `app.communications.integrations.process_pending_communication_events` exists — both are real, tested, idempotent processing functions a future `apps/worker` ARQ schedule can call, but nothing currently invokes them on a timer. This is intentional: `CLAUDE.md` §14's "engine, not scheduler" principle means this phase provides the deterministic mechanism, not the automatic trigger — the same split Phase 9 left for reservation reminder dispatch, and Phase 15 ("Integrations, Automations, Jobs, and Realtime") is where the worker schedule itself is built. No real provider credentials, no per-staff notification preferences/muting, and no authenticated Playwright coverage (the same limitation every phase since 5 has documented — no test Supabase session).

**Manual verification checklist (authenticated workflows, for when a test Supabase session/`storageState` fixture exists):**

1. Sign in and confirm "Communication Hub" appears in the sidebar with its eleven children.
2. `/communications` — dashboard KPI cards render real numbers matching the seeded data.
3. `/communications/inbox` — start a new conversation with an opening message; confirm it appears with an outbound "sent" message (the mock provider accepts every send).
4. Open the conversation, reply with a template selected, and confirm the rendered variables appear correctly; add an internal note and confirm it never appears with an external recipient.
5. Assign the conversation to another staff member and change its priority; confirm both persist and appear in the timeline.
6. Move the conversation through `waiting_on_staff` → `resolved` → `closed`; confirm `reopen` is required to leave `closed` and that an invalid direct transition (e.g. `open` → `closed`) is rejected with 409.
7. `/communications/templates` — create a template referencing an undeclared variable and confirm it is rejected; preview an existing template and confirm the rendered output.
8. `/communications/suppressions` — add a phone number as suppressed, then send a message to that number from a conversation and confirm the message ends in `suppressed` status rather than `sent`.
9. `/communications/preferences` — search for a seeded customer, toggle `do_not_contact`, and confirm a subsequent send attempt is suppressed for that reason.
10. `/communications/channels` — disable a channel's outbound toggle and confirm sends against it are blocked.
11. `/communications/tasks` — create a task, assign it, and step it through `open` → `in_progress` → `blocked` (confirm a reason is required) → `in_progress` → `completed`; confirm `tasks.complete`/`tasks.delete` are enforced for a role without them.
12. `/communications/notifications` — confirm a notification created by a task assignment appears, can be marked read/dismissed, and that "mark all read" clears the unread count.
13. Sign in as a role without `communications.resolve` (e.g. `kitchen_staff`) and confirm resolve/close actions are unavailable and the API returns 403 if called directly.

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

### 13.4 Phase 11 implementation notes and deviations

Phase 11's own explicit instruction gave a much larger functional scope than §13.1–§13.3's 3-table sketch — a 33-numbered-section Knowledge Base and Staff Operations brief (categories, versioned articles, a draft→in_review→changes_requested→approved→published→superseded→archived lifecycle, review/approval, scoped visibility, tags/relationships, attachments, PostgreSQL-only search, version-bound read/acknowledgement tracking, and assignments integrated with the existing Phase 10 task/notification engine). Per `CLAUDE.md` §1.1, that instruction governs this deliverable's actual schema wherever it differs from what is documented above; every deviation actually shipped is recorded here (and, symmetrically, in §14.6 for Staff Operations).

**10 tables, not the 3 named in §13.1–§13.3** (`knowledge_categories`, `knowledge_articles`, `knowledge_article_versions`, `knowledge_article_tags`, `knowledge_article_relations`, `knowledge_visibility_rules`, `knowledge_attachments`, `knowledge_reviews`, `knowledge_assignments`, `knowledge_acknowledgements`), all with RLS enabled, in one migration shared with Staff Operations (`e718e5a70d10_add_phase11_knowledge_base_and_staff_`). `knowledge_folders`/`knowledge_documents` become `knowledge_categories`/`knowledge_articles` — renamed, not added alongside, to match the instruction's own "article" vocabulary and its `article_type` enum (`sop`/`policy`/`procedure`/`checklist`/`guide`/`troubleshooting`/`training_material`/`emergency_instruction`/`announcement`).

**No separate `knowledge_tags` catalog table** — `knowledge_article_tags` is a join table against the single global `tags` table Phase 5 already established for customer/lead tagging, not a second parallel tag vocabulary. The instruction's "reusable tags" requirement is met by reuse, not duplication.

**`KnowledgeArticleRelation` is polymorphic and doubles as the training-course link** (`relation_type` IN `related`/`prerequisite`/`superseded_by`/`referenced_by_training`, with a CHECK constraint rejecting self-relations and a unique constraint rejecting duplicate pairs) — no separate `training_course_articles` join table exists in Staff Operations; a training course referencing supporting articles is the same polymorphic relation with `relation_type = 'referenced_by_training'`.

**Visibility resolution is role-based, not department-based, for `kitchen_only`/`front_of_house_only` scopes** — `app.permissions.seed.DEPARTMENTS` has no dedicated front-of-house department code, so `knowledge_visibility_rules` (scope IN `all_staff`/`department`/`role`/`specific_staff`/`management_only`/`hr_only`/`kitchen_only`/`front_of_house_only`) resolves those two scopes against each staff member's assigned roles rather than a department column that doesn't exist.

**Article versioning is a true immutable snapshot table** (`knowledge_article_versions`: version number, full content/title/summary snapshot, author, published/superseded timestamps) — every material change to a published article creates a new version row rather than mutating the live article; `KnowledgeArticle.published_version_id` always points at the currently live snapshot. Acknowledgements (`knowledge_acknowledgements`) are version-bound (`article_version_id`, not `article_id`) so a new mandatory version automatically invalidates prior acknowledgements — `app.knowledge.assignments` reads "still needs to acknowledge" as "no acknowledgement row for the article's *current* published version," not a separate revocation write.

**Search is PostgreSQL full-text only** — `KnowledgeArticle.search_vector` (a generated `TSVECTOR` column over title/summary/content) with a GIN index, queried through `app.knowledge.search`. No embeddings, pgvector, semantic search, or RAG table exists anywhere in this schema, per `CLAUDE.md` §17's explicit prohibition and this phase's own instruction confirming it.

**Attachments (`knowledge_attachments`) reuse the same private-storage-plus-signed-URL pattern Phase 8's inventory photos and Phase 10's message attachments already established** — no new upload/scanning pipeline was built; `app.knowledge.attachments` is a thin domain wrapper over the existing Supabase Storage adapter.

**Permissions:** 13 new `knowledge.*` codes (`view`, `create`, `update`, `review`, `approve`, `publish`, `archive`, `categories.manage`, `tags.manage`, `visibility.manage`, `assign`, `acknowledge`, `analytics.view`) — there was no Phase 3 placeholder pair to replace (Knowledge Base had no permission codes before this phase).

**Not built in this phase (deferred, not hidden):** no automatic reminder/expiry-warning dispatch — `app.knowledge` exposes deterministic, idempotent query functions only (e.g. articles due for review), matching `CLAUDE.md` §14's "engine, not scheduler" principle already established in Phase 10; automatic dispatch through a live `apps/worker` ARQ schedule is Phase 15's scope. No authenticated Playwright coverage (the same limitation every phase since 5 has documented — no test Supabase session).

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

### 14.6 Phase 11 implementation notes and deviations

Phase 11's own instruction gave Staff Operations a much larger scope than §14.1–§14.5's 5-table sketch — employment profile extension (8-status lifecycle, reporting structure, work location, probation/confirmation dates), staff documents, onboarding/offboarding transition plans, shift templates/rosters/change requests, attendance with corrections, leave management, a training catalogue with attempts and max-attempts enforcement, certifications with expiry/renewal, a skills matrix, performance reviews, disciplinary records, and lightweight availability windows. Every deviation actually shipped is recorded here.

**24 tables, not the 5 named in §14.1–§14.5** (`staff_employment_profiles`, `staff_status_history`, `staff_reporting_history`, `staff_documents`, `staff_transition_templates`, `staff_transition_template_steps`, `staff_transition_plans`, `staff_transition_steps`, `shift_templates`, `staff_shifts`, `shift_change_requests`, `attendance_records`, `attendance_corrections`, `leave_types`, `leave_requests`, `training_courses`, `training_assignments`, `training_attempts`, `staff_certifications`, `skills`, `staff_skills`, `performance_reviews`, `performance_review_goals`, `staff_disciplinary_records`, `staff_availability_windows`), all with RLS enabled, in the same migration as Knowledge Base (`e718e5a70d10_add_phase11_knowledge_base_and_staff_`) — 34 tables total across both domains in this one phase.

**`staff_employment_profiles.lifecycle_status` is deliberately distinct from two pre-existing Phase 3 columns on `staff_users`** — `account_status` (system-login access: active/suspended/etc.) and `employment_status` (actually an employment *type* — full_time/part_time/contract/intern, a Phase 3 naming choice not renamed here to avoid an unrelated breaking migration). `lifecycle_status` is the new 8-state HR lifecycle the instruction asks for (`invited`→`onboarding`→`active`→`on_leave`→`suspended`→`notice_period`→`inactive`→`terminated`), living on the new one-to-one profile table, not on `staff_users` itself.

**Onboarding and offboarding are one `transition_type`-discriminated template/plan/step pair, not two separate schemas** — `staff_transition_templates`/`staff_transition_template_steps`/`staff_transition_plans`/`staff_transition_steps` all carry a `transition_type` (`onboarding`/`offboarding`) column rather than duplicating four tables into eight; the two flows share every structural need (ordered steps, dependencies, approval gates, Phase 10 task integration) and differ only in their step content, which lives in data, not schema.

**`performance_review_cycles` does not exist as a separate table** — cycle fields (`cycle_label`, `period_start_date`, `period_end_date`) are inlined directly onto `performance_reviews`, the same "don't add a table for a 1:1 relationship with no independent lifecycle" judgment Phase 10 made for message template versions.

**Shift overlap detection uses full timestamp ranges, not time-of-day comparison** — `staff_shifts.start_at`/`end_at` are `TIMESTAMPTZ`, so an overnight shift (e.g. 22:00–06:00) needs no special-casing at the midnight boundary; the overlap check is a standard range-intersection query.

**Circular-FK migration pattern used twice** — `staff_employment_profiles.reporting_manager_id` (self-referencing `staff_users`) and the versions↔articles/articles↔categories pairs in Knowledge Base each needed one FK added via `op.create_foreign_key()` after both tables existed, rather than inline in `CREATE TABLE`, and dropped via `op.drop_constraint()` before either table drops in `downgrade()` — a documented Alembic pattern, not a data-model compromise.

**Permissions:** 33 new `staff.*` codes extending (not replacing) the Phase 3 `staff.view`/`staff.manage`/`staff.hr_sensitive.read` triple, which stays scoped to staff *account* administration: `profile.view`/`.manage`, `documents.view`/`.manage`, `onboarding.view`/`.manage`, `offboarding.manage`, `shifts.view`/`.manage`/`.publish`, `shift_changes.request`/`.approve`, `attendance.view`/`.manage`/`.correct`, `leave.view`/`.request`/`.approve`, `training.view`/`.manage`/`.assign`/`.review`, `certifications.view`/`.manage`, `skills.view`/`.manage`, `reviews.view`/`.manage`, `disciplinary.view`/`.manage` (deliberately separate from the broader `staff.hr_sensitive.read`, per `PROJECT_PLAN.md`'s own narrower "strict permissions" bullet for disciplinary records), `availability.view`/`.manage`, and `analytics.view`. Combined with Knowledge Base's 13 codes, the permission registry grew by 46 codes in this phase (152 total).

**Self-service routing bugs found and fixed during API testing:** several endpoints that should allow a staff member to act on their *own* record (complete their own transition step, review their own performance-review self-section, list/create their own availability windows) were initially gated on a broad "view all" permission that self-service roles don't hold; fixed by switching their base dependency to a plain authenticated-user check and adding an internal `_require_self_or_permission(actor, target_staff_id, permission_code)` helper that always allows self-access and falls back to the permission check only for viewing someone else's record. A related over-broad grant (`staff.availability.manage` given to self-service roles for "manage my own availability," which also let them manage everyone else's) was corrected by removing that grant from self-service roles entirely — self-access needs no permission at all — and keeping it only on `hr_manager`.

**Not built in this phase (deferred, not hidden):** no biometric attendance hardware integration (manual and roster-derived attendance only, per this phase's own instruction). No automatic document/certification expiry-warning dispatch — `app.staff_operations` exposes deterministic query functions (`list_documents_expiring_within`, `list_certifications_expiring_within`); automatic dispatch is Phase 15's scope, the same "engine, not scheduler" split as Knowledge Base above. No payroll settlement in offboarding (out of this phase's scope per `PROJECT_PLAN.md`). No complex leave-accrual engine — leave types carry a simple annual `max_consecutive_days` cap, not an accrual ledger. No dummy 65-person staff roster was seeded — every `staff_users` row needs a real Supabase Auth identity and only the bootstrapped owner account exists in this environment (consistent with `PROJECT_PLAN.md` §4's canonical dummy total remaining a documented target figure, not seeded data). No authenticated Playwright coverage (the same limitation every phase since 5 has documented).

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

Shipped in Phase 10 with the extensions (`priority`, `dismissed_at`, `actioned_at`, `dedup_key`) recorded in §12.5 — this sketch remains the base shape.

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

Phase 7 shipped its own narrower endpoint set matching §10.7's deviations (no cancel/refund-request/inventory-reservations endpoints — cancellation is a `transition` target, there is no refund workflow or inventory reservation) — see §10.7 for the full reasoning. The endpoints below remain the target once payment-gateway integration and inventory reservation exist. Phase 7's actual surface: `GET/POST /api/v1/orders`, `GET/PATCH /api/v1/orders/{order_id}`, `POST /api/v1/orders/{order_id}/transition`, `POST /api/v1/orders/{order_id}/assign`, `GET /api/v1/orders/{order_id}/timeline`, `GET /api/v1/orders/{order_id}/status-history`, `GET/POST /api/v1/orders/{order_id}/payments`, `PATCH /api/v1/orders/{order_id}/payments/{payment_id}`, `GET/POST /api/v1/orders/{order_id}/notes`, `GET /api/v1/orders/dashboard/stats`, `GET /api/v1/orders/search-customers`.

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

Phase 8's actual router (`app/inventory/router.py`, 43 endpoints under `/api/v1/inventory`) — see §9.8 for the full set of implementation deviations this reflects. Suppliers live under `/api/v1/inventory/suppliers`, not the top-level `/api/v1/suppliers` this section previously documented.

- Reference data: `GET/POST /units`, `PATCH /units/{id}`; `GET/POST /categories`, `PATCH /categories/{id}`; `GET/POST /locations`, `PATCH /locations/{id}`; `GET/POST /suppliers`, `GET/PATCH/DELETE /suppliers/{id}`, `POST /suppliers/{id}/restore`
- Items: `GET/POST /items`, `GET/PATCH/DELETE /items/{id}`, `POST /items/{id}/restore`, `GET /items/{id}/balances`, `GET /items/{id}/batches`, `GET /items/{id}/movements`
- Global ledger: `GET /movements`; `GET /balances/verify`, `POST /balances/rebuild`
- Receipts: `GET/POST /receipts`, `GET /receipts/{id}`, `POST /receipts/{id}/items`, `POST /receipts/{id}/post`, `POST /receipts/{id}/reverse`
- Adjustments: `GET/POST /adjustments`
- Wastage: `GET/POST /wastage`
- Transfers: `GET/POST /transfers`, `GET /transfers/{id}`, `POST /transfers/{id}/items`, `POST /transfers/{id}/post`, `POST /transfers/{id}/reverse`
- Stock counts: `GET/POST /counts`, `GET /counts/{id}`, `POST /counts/{id}/start`, `PATCH /counts/{id}/lines/{line_id}`, `POST /counts/{id}/submit`, `POST /counts/{id}/approve`, `POST /counts/{id}/cancel`
- Recipes: `GET/POST /recipes`, `GET /recipes/resolve`, `GET/DELETE /recipes/{id}`, `GET /recipes/{id}/cost`, `POST /recipes/{id}/items`
- Dashboard: `GET /dashboard/stats`

Every stock mutation is permission-checked against the 26-code registry in §9.8 (`inventory.items.create`/`.update`/`.archive`/`.restore`, `.receipts.create`/`.post`/`.reverse`, `.adjustments.create`/`.approve`, `.wastage.create`/`.approve`, `.transfers.create`/`.post`/`.reverse`, `.counts.create`/`.submit`/`.approve`, `.recipes.view`/`.manage`, `.balances.rebuild`, plus `.view`/`.cost.view`/`.units.manage`/`.categories.manage`/`.locations.manage`/`.suppliers.manage`), audited, and posts through the append-only ledger transactionally.

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

All under `/api/v1/knowledge`, per §13.4's actual 10-table schema:

- Categories: `GET/POST /categories`, `PATCH /categories/{id}`
- Search and analytics: `GET /search`, `GET /analytics`
- Articles: `GET/POST /articles`, `GET/PATCH /articles/{id}`, `POST /articles/{id}/submit`, `POST /articles/{id}/review`, `POST /articles/{id}/publish`, `POST /articles/{id}/transition`, `GET /articles/{id}/versions`, `GET /articles/{id}/timeline`
- Tags: `POST /articles/{id}/tags`, `DELETE /articles/{id}/tags/{tag_id}`
- Relations: `GET/POST /articles/{id}/relations`, `DELETE /articles/{id}/relations/{relation_id}`
- Visibility rules: `GET/POST /articles/{id}/visibility-rules`, `DELETE /articles/{id}/visibility-rules/{rule_id}`
- Attachments: `GET/POST /articles/{id}/attachments`, `GET /articles/{id}/attachments/{attachment_id}/signed-url`, `DELETE /articles/{id}/attachments/{attachment_id}`
- Assignments and acknowledgement: `GET/POST /articles/{id}/assignments`, `POST /articles/{id}/assignments/{assignment_id}/cancel`, `POST /articles/{id}/acknowledge`, `GET /acknowledgements/mine`

32 endpoints total. Uploads use the existing Supabase Storage adapter's quarantine and scanning pipeline. Download URLs are short-lived and permission checked. Every mutation is checked against the 13-code `knowledge.*` registry in §13.4.

## 29. STAFF AND HR API

All under `/api/v1/staff-operations`, per §14.6's actual 24-table schema (in addition to the pre-existing Phase 3 `/api/v1/staff-users` administration endpoints, which this router does not replace):

- Employment profiles: `GET/POST /profiles`, `GET /profiles/{staff_user_id}`, `PATCH /profiles/{staff_user_id}`, `POST /profiles/{staff_user_id}/transition`
- Documents: `GET/POST /documents`, `POST /documents/{id}/verify`
- Onboarding/offboarding: `GET/POST /transition-templates`, `POST /transition-templates/{id}/steps`, `GET/POST /transition-plans`, `GET /transition-plans/{id}/steps`, `POST /transition-steps/{id}/complete`, `POST /transition-steps/{id}/approve`
- Shifts and roster: `GET/POST /shift-templates`, `GET/POST /shifts`, `PATCH /shifts/{id}`, `POST /shifts/{id}/publish`, `GET/POST /shift-change-requests`, `POST /shift-change-requests/{id}/decide`
- Attendance: `GET/POST /attendance`, `POST /attendance/{id}/correct`
- Leave: `GET/POST /leave-types`, `GET/POST /leave-requests`, `POST /leave-requests/{id}/decide`, `POST /leave-requests/{id}/withdraw`
- Training: `GET/POST /training/courses`, `GET/POST /training/assignments`, `POST /training/assignments/{id}/attempts`, `GET /training/assignments/{id}/attempts`, `POST /training/attempts/{id}/complete`
- Certifications: `GET/POST /certifications`, `POST /certifications/{id}/verify`
- Skills: `GET/POST /skills`, `GET /staff-skills/{staff_user_id}`, `PUT /staff-skills/{staff_user_id}`
- Performance reviews: `GET/POST /reviews`, `PATCH /reviews/{id}`, `POST /reviews/{id}/transition`
- Disciplinary: `GET/POST /disciplinary-records`
- Availability: `GET/POST /availability/{staff_user_id}`
- Analytics: `GET /analytics`

58 endpoints total. HR-sensitive fields (address, restricted notes) require `staff.documents.view`/the dedicated Phase 3 `staff.hr_sensitive.read` permission and are excluded from ordinary profile responses via a separate `EmploymentProfileSensitive` schema. Self-service endpoints (a staff member's own transition steps, availability windows, review self-section, training attempts) use `_require_self_or_permission` rather than a blanket "view all" permission — see §14.6. Every mutation is checked against the 33-code `staff.*` registry in §14.6.

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

Superseded by §30.5's full endpoint list (Phase 13's actual API surface across three routers). Kept here as the original sketch for history:

- `GET /api/v1/feedback`
- `POST /api/v1/feedback`
- `GET /api/v1/complaints`
- `POST /api/v1/complaints`
- `GET /api/v1/complaints/{id}`
- `PATCH /api/v1/complaints/{id}`
- `POST /api/v1/complaints/{id}/assign`
- `POST /api/v1/complaints/{id}/transition`
- `POST /api/v1/complaints/{id}/recovery-action`

### 30.4 Phase 12 implementation notes and deviations

Phase 12's actual API surface (nine domain routers, superseding §30.1's four-endpoint sketch, which predated the scope expansion recorded in `ROADMAP.md`'s Phase 12 completion notes):

- `/api/v1/loyalty` — `programs`, `programs/{id}` (PATCH, `/transition`), `tiers`, `accounts` (GET by `customer_id`, POST to enroll), `accounts/{id}/ledger`, `earn`, `redeem`, `adjust`, `reverse`, `accounts/{id}/tier`, `analytics`.
- `/api/v1/segments` — CRUD + `/transition`, `/members` (list/add/remove), `/refresh`, `/preview`.
- `/api/v1/offers` — CRUD + `/versions`, `/transition`, `/coupons`, `/preview`, `redemptions/reserve`, `redemptions/{id}` (`/confirm`, `/reject`, `/reverse`).
- `/api/v1/campaigns` — CRUD + `/transition`, `/audience/build`, `/recipients`, `/launch`, `/sync`, `/analytics`.
- `/api/v1/referrals` — `programs` (CRUD + `/transition`, `/codes`), `codes/{code}`, `relationships` (list + `/attribute`, `/{id}/qualify`, `/{id}/reject`, `/{id}/reward`).
- `/api/v1/achievements` — CRUD + `/evaluate`, `awards/{id}` (GET, `/reverse`).
- `/api/v1/gift-cards` — CRUD (issue only, no update) + `/analytics`, `/{id}/reveal`, `/{id}` status actions (`activate`/`suspend`/`reinstate`/`cancel`/`expire`), `/{id}/adjust`, `/{id}/ledger`, `/redeem`, `/reverse`.
- `/api/v1/customer-credit` — `accounts` (GET by `customer_id`, POST to open), `accounts/{id}/ledger`, `issue`, `redeem`, `adjust`, `reverse`, `analytics`.
- `/api/v1/commercial-risk` — `flags` (list + GET by id), `flags/{id}/review`.

Key implementation decisions, in addition to §1.1's ROADMAP scope-expansion note:

- **Shared, closed rule engine** (`app.commercial_rules`): a `RuleNode` tree (`RuleCondition` leaves combined by `RuleGroup` `all`/`any`/`not` logic) is the *only* mechanism Segments' `rule_definition`, Offers' `eligibility_rule`, and Achievements' `condition` accept — `fact` is restricted to a closed `SUPPORTED_FACTS` tuple resolved from real CRM data (`app.commercial_rules.facts.resolve_customer_facts`), never an arbitrary expression. `app.offers.benefit.BenefitRule` is a parallel closed discriminated union for offer payout math, validated against the offer's `offer_type` at creation.
- **Ledger pattern replicated three times**: `loyalty_ledger_entries`, `gift_card_ledger_entries`, and `customer_credit_ledger_entries` all mirror Phase 8's `inventory_ledger` guarantees — append-only, signed deltas keyed by `entry_type`, idempotency-keyed (`VARCHAR(160)`, callers with unbounded-length source keys must hash them, not embed them verbatim), and `SELECT ... FOR UPDATE` row-locked before balance mutation.
- **Order-lifecycle integration is additive**: `app.orders.commercial_growth_integration.apply_commercial_growth_effects` runs *after* Phase 7's unmodified state machine (the same "integrate without weakening validation" model Phase 8's `inventory.order_integration` established), writing `Customer.completed_order_count`/`lifetime_value_minor`/`average_order_value_minor`/`first_order_at`/`last_order_at` on `completed` — a Phase 7 responsibility its own docstring described but no Phase 7 code path ever fulfilled, fixed here rather than deferred since every Phase 12 rule evaluation depends on those columns being fresh. Loyalty earn and referral qualification are gated on `payment_status == "paid"`; the customer roll-up and achievement evaluation are not (an unpaid completed order is still a fulfilled order for count/spend purposes).
- **`GET /segments/{id}/members` returns `PaginatedResponse[uuid.UUID]`** (bare current-member customer ids), not `SegmentMembership` rows — `SegmentMembership` is the add/remove *event* record returned by the mutation endpoints. Frontend `useSegmentMembers` types against the correct `string[]` shape.
- **Gift cards, customer credit, and commercial-risk flags are intentionally not seeded** — this phase's own rule against fabricating real-value grants to arbitrary customers or synthetic risk events (`app/db/seed.py`'s own comment). All other eight domains have idempotent seed data.
- **Frontend navigation**: all nine domains nest as `children` under the single existing "Marketing, Loyalty & Feedback" nav section (`/marketing/loyalty`, `/marketing/segments`, `/marketing/offers`, `/marketing/campaigns`, `/marketing/referrals`, `/marketing/achievements`, `/marketing/gift-cards`, `/marketing/customer-credit`, `/marketing/commercial-risk`) rather than adding new top-level sections, per CLAUDE.md §2's fixed twelve-section rule. The section is now permission-gated (`requiredPermission`, OR-matched across all nine domains' `.view` codes) — previously an ungated placeholder.
- **Rule-tree authoring is intentionally scoped down in the UI**: Segments/Offers/Achievements creation forms build a single `RuleCondition` (fact/operator/value), not an arbitrary nested `RuleGroup` tree — the backend accepts full trees (and a read-only `summarizeRuleNode` renderer displays any tree, including ones the UI itself never authors), but a visual AND/OR tree builder was judged out of scope for this phase's lightweight-controls framing. Extending the UI to author nested groups is a natural, self-contained follow-up.
- **Customer 360 integration**: a new "Commercial" tab on the customer detail page (`apps/dashboard/src/app/(app)/customers/[customerId]/customer-commercial-summary.tsx`) surfaces loyalty points/tier, gift card count and balances, customer-credit balance, and open commercial-risk flag count via the domain hooks directly (no new backend aggregation endpoint) — matching the tab-per-domain pattern established by the existing addresses/notes/tags tabs, since no combined per-customer commercial-summary endpoint exists or was judged necessary.

### 30.5 Phase 13 implementation notes and deviations

Phase 13's actual API surface (three domain routers, superseding §30.3's nine-endpoint sketch):

- `/api/v1/feedback` — CRUD (list/create/get/update) + `/transition`, `/convert-to-complaint`, `/tags`, `/ratings`, `/status-history`, `/analytics`, `/customers/{customer_id}/history`.
- `/api/v1/review-requests` — list/create/get + `/complete`, `/cancel`, `/process-pending` (the deterministic engine entry point), `/analytics`.
- `/api/v1/complaints` — CRUD (list/create/get/update) + `/transition`, `/assign`, `/escalate`, `/root-cause`, `/notes`, `/follow-ups`, `follow-ups/{id}/complete`, `/links`, `/timeline`, `/analytics`, `/sla-policies` (list/create), `/sla-policies/{id}` (PATCH), `/sla/run-escalations` (the deterministic engine entry point), `/{id}/recovery-actions` (list/propose — nested here since a recovery action always originates from a specific complaint).
- `/api/v1/service-recovery` — `/actions` (list) + `/actions/{id}` (get, `/approve`, `/reject`, `/execute`, `/reverse`, `/history`), `/analytics`, `/approval-rules` (list/create/update).

Key implementation decisions:

- **Business-hours-aware SLA due-date calculator is genuinely new** (`app.complaints.sla.compute_due_at`): no "add N business minutes, skipping closed periods" calculator existed anywhere in the codebase before this phase. It walks forward day-by-day in `Asia/Kolkata` local time (bounded to 60 days as a safety net), reading Phase 9's `business_hours`/`holiday_calendar` tables as the single source of truth rather than re-deriving them. `select_sla_policy` picks the most specific active policy matching both category and severity (a `NULL` list on either field matches any value); `detect_sla_events` is idempotent (`dedup_key` unique per complaint+milestone+approaching-or-breached) and is the deterministic engine `run_sla_escalations` calls to also create a deduplicated `TaskRecord` and notification per event, auto-escalating on `breached_resolution` when the matched policy configures `escalation_after_minutes`.
- **Value-threshold compensation-approval routing is genuinely new** (`app.service_recovery.service.evaluate_approval_requirement`): confirmed during research that `customer_credit.approve` was granted in the role matrix but never actually checked against a threshold anywhere in the live codebase. `CompensationApprovalRule` matches on `recovery_type` (`NULL` = any), a `min_value_minor`/`max_value_minor` range (money-denominated types only), and `applicable_severities` (`NULL` = any); the most specific matching *active* rule governs, and its mere existence is what makes an action `approval_required`. `approve_action` blocks the proposer from approving their own action unless the matched rule sets `allow_self_approval=True`.
- **Service recovery execution never mutates a balance directly**: `_dispatch_execution` calls `app.loyalty.ledger.post_entry(entry_type="service_recovery_credit")` for `loyalty_credit`, `app.orders.service.update_payment_status(new_status="refunded")` for `approved_refund`/`discount` (only when the complaint has a linked order with a `paid` payment — otherwise falls through to `manual`), and records only `execution_reference_type`/`execution_reference_id`. Types with no automatable ledger (`apology_only`, `replacement`, `refund_request`, `coupon`, `complimentary_item`, `manager_follow_up`, `operational_correction`) are recorded as `execution_reference_type="manual"` — an honest gap, not a fabricated integration (CLAUDE.md §16). On successful execution, `Customer.customer_segment` is set to `"complaint_recovery"` unless already `"vip"`.
- **Mutual feedback↔complaint reference resolved with a deferred FK**: `feedback_entries.converted_to_complaint_id` and `complaints.feedback_id` reference each other; the model column declares no FK, and the migration adds `fk_feedback_entries_converted_to_complaint_id_complaints` via `op.create_foreign_key` after both tables exist (dropped first in `downgrade()`, before either table's `DROP TABLE`) — the same deferred-FK technique every prior phase's own circular-schema needs used.
- **Three polymorphic CHECK constraints widened, not a second column added**: `TaskRecord.related_type` (+`complaint`, `feedback`), `ConversationLink.linked_type` (+`complaint`; `feedback_case` already existed from Phase 10), and `Notification.record_type` (+`complaint`, `service_recovery_action`) — the last one caught only by actually running the seed script end-to-end, not by static review, and fixed in both the model and this phase's own migration rather than a follow-up one. All three use raw `ALTER TABLE ... DROP/ADD CONSTRAINT` SQL, not `op.create_check_constraint`/`op.drop_constraint` (which double-apply the naming-convention template on an already-qualified constraint name).
- **HR-sensitive complaint gating models the existing staff sensitive-overlay pattern**: `Complaint.is_hr_sensitive` is set at creation (`True` when `category == "staff_behavior"`), and `complaints.hr_sensitive.read` gates viewing beyond the base `complaints.view`/`complaints.view_all` — the same base-plus-sensitive-overlay shape `staff.view`/`staff.hr_sensitive.read` already established, chosen by analogy since no document defined this interaction precisely.
- **Read-time timeline aggregation, not a new generic timeline table**: `app.complaints.service.build_timeline` aggregates across five existing tables (status history, assignments, notes, escalations, follow-ups) sorted by `occurred_at` — CLAUDE.md's own instruction not to duplicate a generic timeline mechanism.
- **Cross-module integrations are all additive**, run after the owning phase's own unmodified state machine: `app.feedback.integrations.schedule_order_review_request`/`schedule_reservation_review_request` are called from `app/orders/router.py`/`app/reservations/router.py`'s `transition` endpoints after the core transition succeeds, swallowing `DuplicateReviewRequestError`/`FeedbackError` so a retried transition or domain-level rejection never breaks the underlying order/reservation transition; `app.complaints.integrations.link_complaint_conversation` ensures every complaint has a backing Communication Hub conversation, reusing (not duplicating) `app.communications.integrations`'s existing get-or-create-by-linked-record helper.
- **Frontend navigation**: feedback/complaints/service-recovery nest as `children` under the existing "Marketing, Loyalty & Feedback" nav section (`/marketing/feedback`, `/marketing/complaints`, `/marketing/service-recovery`) rather than a new top-level section — CLAUDE.md §2's fixed twelve-section rule, and the section's own name already says "& Feedback". `/marketing/feedback` and `/marketing/complaints` each use a tabbed workspace to avoid nav sprawl (Feedback/Review Requests; Complaints/SLA Policies); `/marketing/complaints/{id}` is a full operational workspace including an embedded service-recovery panel.
- **Customer 360 integration**: a new "Feedback" tab (`apps/dashboard/src/app/(app)/customers/[customerId]/customer-feedback-summary.tsx`) surfaces recent feedback (rating/sentiment/status), complaint severity/resolution state, and recovery-action history for that customer via the domain hooks directly, matching the Phase 12 "Commercial" tab's pattern.

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

### 31.6 Phase 14 implementation notes and deviations

Phase 14's actual API surface (six domain routers under `apps/api/app/{analytics_core,reports,report_exports,report_schedules,anomalies,forecasts,controlled_ai}`, superseding §31.1–§31.3's original sketch, 30 endpoints total across `/api/v1/analytics`, `/api/v1/dashboard/{domain}`, `/api/v1/reports`, `/api/v1/exports`, `/api/v1/report-schedules`, `/api/v1/anomalies`, `/api/v1/forecasts`, and `/api/v1/ai`):

- **Deterministic analytics-first architecture, not a generic query engine**: `app.analytics_core.registry.METRICS` is a hand-written, in-code registry of 35 `MetricDef`s, each mapped to one hand-written SQLAlchemy calculator function. There is no dynamic query builder, no user-composable filter/aggregate DSL, and no arbitrary SQL surface anywhere in this phase — every metric a client can request is a fixed, reviewed query. `app.analytics_core.engine.run_metric_query` re-checks `required_permission` against the caller's current effective permissions on every call (never cached across the request).
- **Window resolution is centralized**: `app.analytics_core.windows.resolve_window` computes UTC-normalized `[start, end)` boundaries in `Asia/Kolkata` for the nine `REPORT_WINDOW_CODES` (`today`/`yesterday`/`current_week`/`previous_week`/`current_month`/`previous_month`/`current_quarter`/`previous_quarter`/`custom`), with an automatic equivalent-length prior-period comparison window for every non-custom code. `custom` is capped at `MAX_CUSTOM_RANGE_DAYS = 366`.
- **Zero-denominator safety**: percentage change (`_pct_change` in `app.analytics_core.engine`) returns `None`, never a fabricated `0%`/`100%`, when the comparison value is zero.
- **Partial-failure-tolerant dashboards**: `app.reports.service.get_dashboard` silently skips (returns in a separate `skipped` list, exposed to the frontend as `DashboardOut.partial_failures`) any metric the caller lacks permission for, rather than failing the whole dashboard. 11 dashboard domains are wired (`executive`, `sales`, `customers`, `leads`, `reservations`, `inventory_suppliers`, `marketing`, `loyalty`, `feedback`, `complaints`, `staff_tasks`) — one more than this phase's "10 required dashboard views" framing, since `executive` is the cross-domain overview and the ten domain-specific views cover the rest.
- **Drilldown is a small, hand-written allowlist, not a generic per-metric mechanism**: `app.reports.service.get_drilldown` explicitly handles 7 metric codes (`exec_open_high_severity_complaints`, `leads_open`, `inventory_low_stock_items`, `inventory_critical_stock_items`, `sales_cancelled_order_count`, `staff_overdue_tasks`, `reservations_no_show_rate`) with direct, bounded (`LIMIT 100`) queries against the owning domain's tables. This is a deliberate scoping decision, not an oversight — every other metric on a dashboard renders without a drilldown affordance.
- **Immutable report runs, one documented deviation**: `ReportRun` uses `TimestampMixin`, not `AppendOnlyTimestampMixin`, because it has a real `pending → running → completed/failed` lifecycle — but is never mutated again once it reaches a terminal status (enforced at the service layer). This mirrors the `ComplaintEscalation` precedent from Phase 13. `ReportRunDataset` (the actual computed metric snapshot) is genuinely append-only, written exactly once per run.
- **Export engine uses the two locked libraries from `docs/TOOLS.md`**: openpyxl for XLSX (never macro-enabled `.xlsm`), Playwright + Chromium for PDF. CSV export sanitizes formula-injection payloads (a leading apostrophe is prepended to any cell starting with `=`, `+`, `-`, `@`, tab, or CR — the OWASP CSV-injection mitigation) and writes a UTF-8 BOM for Excel compatibility.
- **"Engine, not scheduler" — the same split every phase since Phase 9's reminder system has used**: `app.report_schedules.service.execute_due_occurrence`, `app.anomalies.engine.evaluate_all_active_rules`, and `app.forecasts.service.run_forecast` are deterministic, idempotent, directly-callable functions with zero live cron/ARQ wiring in this phase. Recurring dispatch through `apps/worker` is explicitly Phase 15's scope.
- **Scheduled-report delivery re-checks permissions twice, never from a cache**: `execute_due_occurrence` re-fetches the report owner's *current* effective permissions immediately before generating (an owner who lost `reports.view` since the schedule was created gets a skipped, not a stale, run), and separately re-checks each staff recipient's `reports.view` at delivery time — a recipient who lost access is silently skipped, not sent a stale-permission report. `ReportDeliveryAttempt` has a unique constraint on `(scheduled_report_id, occurrence_key, recipient_reference)` for delivery idempotency.
- **Six anomaly rule types**: `absolute_threshold`, `pct_change_prior_period`, `rolling_average_deviation`, `count_rate_threshold` (evaluated identically to `absolute_threshold` — same comparison, different semantic label for the caller), `consecutive_deterioration`, `missing_activity`. Deduplication is via `AnomalyFinding.dedup_key` (a unique constraint) plus a `cooldown_hours` time-window suppression, so a persistently-anomalous metric doesn't spawn a new finding on every evaluation cycle. Finding lifecycle is `open → {acknowledged, dismissed}`, `acknowledged → {investigating, resolved, dismissed}`, `investigating → {resolved, dismissed}` — `resolved`/`dismissed` are terminal.
- **Four transparent, auditable forecast methods only — no black-box ML**: `moving_average`, `linear_trend` (ordinary least squares), `seasonal_naive`, `exponential_smoothing` (level-only; no trend or seasonality component — a documented limitation, not a bug). A snapshot with fewer than `minimum_history_periods` of non-zero history returns `status="insufficient_data"` rather than a fabricated projection. Each snapshot records a holdout-based `backtest_mae`/`backtest_mape` so the forecast's own historical accuracy is visible, not just asserted.
- **Controlled AI is 5 of 19 `AI_FEATURE_CODES`, not all of them**: `dashboard_summary`, `metric_change_explanation`, `anomaly_evidence_summary`, `report_narrative`, and `nl_question_query_plan` have working prompt templates (`app.controlled_ai.prompts.PROMPT_TEMPLATES`) and grounding (`app.controlled_ai.grounding`) in this phase — the five capabilities central to "Reports, Analytics, and Controlled AI" itself. The remaining 14 feature codes exist in the closed `AI_FEATURE_CODES` list for future phases to wire their own grounding against, but `app.controlled_ai.service.request_completion` rejects any feature code without a registered template rather than running it ungrounded. `nl_question_query_plan` is a query-*plan* proposal only (a `metric_code` + `window_code` the model selects from an allowlist it's given) — the server validates the proposed `metric_code` against the real metric registry before anything runs; the model never writes or executes SQL. Provider selection (`app.controlled_ai.providers.get_ai_provider`) falls back OpenAI → Groq → Mock based on which API key is configured, so the feature works end-to-end (deterministically, via `MockAiProvider`) with zero external credentials configured — consistent with §21's "development must be possible before all production credentials are available."
- **RLS enabled on all 16 new tables**, matching every table since the Phase-3-era RLS migration; `apps/api` itself connects as table owner and bypasses RLS, so this is specifically the Supabase `anon`/PostgREST bypass-prevention layer, not `apps/api`'s own authorization (which remains the FastAPI permission-dependency layer).
- **Naming convention drove renames during this phase**: any permission code ending in `.view` is automatically granted to `read_only_auditor` via `app.permissions.role_matrix._ALL_VIEW`, which is why the metric-domain view permissions are `analytics.executive.view` / `analytics.sales.view` / … (not `analytics.view_executive`) and the AI usage-visibility permission is `ai.analytics.usage.view` (not `ai.analytics.view_usage`) — matching every other domain's `<domain>.<subject>.view` shape.
- **Frontend consolidation, a deliberate scope decision**: rather than ten near-duplicate dashboard page files, the eleven dashboard domains share one `DomainDashboardView` component (`apps/dashboard/src/app/(app)/reports/domain-dashboard-view.tsx`) parameterized by `domain`/`title`/`description`, with thin per-route `page.tsx` files. The "Reports, Analytics & AI Center" nav section gained two additional children beyond the phase prompt's original nine-route sketch (`Loyalty` and `Complaints`) so every one of the eleven backend dashboard domains has a reachable page — `CLAUDE.md` §2 still fixes the CRM at exactly twelve top-level sections; this only adds children under the existing one.
- **Customer 360 / domain drilldown integration**: rather than a bespoke drilldown surface embedded in each of Customer 360 / Order / Inventory / Reservation / Campaign / Complaint / Staff, drilldown is centralized in `DomainDashboardView`'s own modal (backed by `GET /api/v1/reports/drilldown`) across every dashboard that surfaces one of the seven allowlisted metric codes above — clicking any other metric card is inert by design, since no drilldown query exists for it yet.

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
