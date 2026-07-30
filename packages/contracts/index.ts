// Shared API contracts, error shapes, and pagination definitions —
// ARCHITECTURE_AND_TECH_STACK.md section 5.5. Backend types remain
// authoritative; this package must be refreshed through a documented
// process, not hand-duplicated ahead of the backend schema.

export type ErrorCode =
  | "validation_error"
  | "authentication_required"
  | "permission_denied"
  | "not_found"
  | "conflict"
  | "invalid_state_transition"
  | "rate_limited"
  | "external_dependency_unavailable"
  | "integration_configuration_error"
  | "retryable_processing_failure"
  | "internal_error";

export interface ApiErrorBody {
  error: {
    code: ErrorCode;
    message: string;
    field_errors?: Record<string, string[]>;
    request_id: string;
  };
}

export interface Meta {
  request_id: string;
}

export interface DataResponse<T> {
  data: T;
  meta: Meta;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: Pagination;
  meta: Meta;
}

// --- Phase 3: Authentication, Users, Roles, and Permissions ---
// Mirrors apps/api/app/auth/schemas.py, apps/api/app/staff/schemas.py, and
// apps/api/app/roles/schemas.py. Keep these in sync by hand until a
// generation step exists — ARCHITECTURE_AND_TECH_STACK.md section 5.5.

export type AccountStatus = "invited" | "active" | "suspended" | "disabled" | "locked" | "archived";
export type EmploymentStatus = "full_time" | "part_time" | "contract" | "intern";
export type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";

export interface RoleRef {
  id: string;
  code: string;
  name: string;
}

export interface CurrentUser {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string | null;
  display_name: string;
  email: string;
  phone_e164: string | null;
  department_id: string | null;
  job_title: string | null;
  account_status: AccountStatus;
  employment_status: EmploymentStatus;
  is_privileged: boolean;
  last_login_at: string | null;
  timezone: string;
  avatar_storage_path: string | null;
  preferred_language: string | null;
  roles: RoleRef[];
  permissions: string[];
}

export interface StaffUserListItem {
  id: string;
  employee_code: string;
  display_name: string;
  email: string;
  department_id: string | null;
  job_title: string | null;
  account_status: AccountStatus;
  employment_status: EmploymentStatus;
  is_privileged: boolean;
}

export interface StaffUserDetail {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string | null;
  display_name: string;
  email: string;
  phone_e164: string | null;
  department_id: string | null;
  job_title: string | null;
  account_status: AccountStatus;
  employment_status: EmploymentStatus;
  is_privileged: boolean;
  last_login_at: string | null;
  timezone: string;
  avatar_storage_path: string | null;
  preferred_language: string | null;
  roles: RoleRef[];
}

export interface Department {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface RoleListItem {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_system_role: boolean;
  is_active: boolean;
}

export interface Permission {
  id: string;
  code: string;
  module: string;
  action: string;
  description: string | null;
  is_sensitive: boolean;
}

export interface RolePermissions {
  role: RoleListItem;
  permission_codes: string[];
}

export interface Invitation {
  id: string;
  email: string;
  first_name: string;
  last_name: string | null;
  department_id: string | null;
  intended_role_id: string;
  status: InvitationStatus;
  invited_at: string;
  expires_at: string;
}

// --- Phase 5: Customers and Leads ---
// Mirrors apps/api/app/customers/schemas.py and apps/api/app/leads/schemas.py.

export type CustomerType = "individual" | "corporate";
export type CustomerStatus = "active" | "inactive" | "blacklisted" | "archived" | "merged";
export type CustomerSegment =
  | "new"
  | "repeat"
  | "loyal"
  | "vip"
  | "at_risk"
  | "dormant"
  | "high_aov"
  | "family"
  | "corporate"
  | "college_group"
  | "delivery_first"
  | "dine_in_first"
  | "discount_sensitive"
  | "complaint_recovery";
export type DietaryPreference = "vegetarian" | "non_vegetarian" | "vegan" | "jain" | "no_preference";
export type SpicePreference = "mild" | "medium" | "spicy" | "extra_spicy";
export type NoteType =
  | "general"
  | "service_preference"
  | "complaint"
  | "recovery"
  | "corporate"
  | "delivery"
  | "reservation"
  | "dietary";
export type ConsentType =
  | "whatsapp_marketing"
  | "email_marketing"
  | "sms_marketing"
  | "loyalty"
  | "feedback_request"
  | "personalization";
export type ConsentStatus = "granted" | "withdrawn" | "unknown";

export interface CustomerListItem {
  id: string;
  customer_number: string;
  display_name: string;
  customer_type: CustomerType;
  primary_phone_e164: string | null;
  primary_email: string | null;
  customer_status: CustomerStatus;
  customer_segment: CustomerSegment | null;
  assigned_staff_id: string | null;
  completed_order_count: number;
  lifetime_value_minor: number;
  last_order_at: string | null;
}

export interface Customer {
  id: string;
  customer_number: string;
  customer_type: CustomerType;
  first_name: string | null;
  last_name: string | null;
  organization_name: string | null;
  display_name: string;
  primary_phone_e164: string | null;
  primary_email: string | null;
  date_of_birth: string | null;
  anniversary_date: string | null;
  preferred_language: string | null;
  dietary_preference: DietaryPreference | null;
  spice_preference: SpicePreference | null;
  customer_status: CustomerStatus;
  customer_segment: CustomerSegment | null;
  acquisition_source: string | null;
  assigned_staff_id: string | null;
  first_order_at: string | null;
  last_order_at: string | null;
  completed_order_count: number;
  lifetime_value_minor: number;
  average_order_value_minor: number;
  last_activity_at: string | null;
  merged_into_customer_id: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface CustomerAddress {
  id: string;
  customer_id: string;
  label: string | null;
  recipient_name: string | null;
  phone_e164: string | null;
  address_line1: string;
  address_line2: string | null;
  landmark: string | null;
  locality: string | null;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  latitude: string | null;
  longitude: string | null;
  delivery_instructions: string | null;
  is_default: boolean;
  is_active: boolean;
}

export interface CustomerNote {
  id: string;
  customer_id: string;
  note_type: NoteType;
  content: string;
  is_sensitive: boolean;
  created_by: string;
  created_at: string;
  updated_at: string | null;
  updated_by: string | null;
}

export interface Tag {
  id: string;
  name: string;
  normalized_name: string;
  description: string | null;
  is_active: boolean;
}

export interface CustomerConsent {
  id: string;
  customer_id: string;
  consent_type: ConsentType;
  status: ConsentStatus;
  source: string;
  policy_version: string | null;
  granted_at: string | null;
  withdrawn_at: string | null;
}

export interface DuplicateCustomerMatch {
  customer: CustomerListItem;
  match_reasons: string[];
}

export interface MergePreview {
  source: Customer;
  surviving: Customer;
  conflicting_fields: string[];
  source_address_count: number;
  source_tag_count: number;
  source_note_count: number;
}

export interface TimelineEntry {
  id: string;
  action_code: string;
  actor_id: string | null;
  created_at: string;
  safe_metadata: Record<string, unknown> | null;
}

export type LeadType =
  | "corporate_catering"
  | "recurring_office_order"
  | "event_booking"
  | "group_dining"
  | "partnership"
  | "franchise_or_business_enquiry"
  | "general_sales_enquiry";
export type LeadSource =
  | "website"
  | "phone"
  | "walk_in"
  | "whatsapp"
  | "zomato_import"
  | "swiggy_import"
  | "meta_campaign"
  | "google_campaign"
  | "referral"
  | "corporate_outreach"
  | "event_enquiry"
  | "offline_qr";
export type LeadStatus =
  | "new"
  | "contacted"
  | "qualified"
  | "interested"
  | "follow_up_scheduled"
  | "proposal_shared"
  | "negotiating"
  | "won"
  | "lost"
  | "closed";
export type LeadPriority = "low" | "normal" | "high" | "urgent";
export type LostReason =
  | "budget"
  | "timing"
  | "no_response"
  | "chose_competitor"
  | "service_unavailable"
  | "location_issue"
  | "menu_mismatch"
  | "duplicate"
  | "invalid_enquiry";
export type LeadActivityType =
  | "call"
  | "email"
  | "whatsapp"
  | "meeting"
  | "proposal"
  | "note"
  | "status_change"
  | "assignment"
  | "follow_up_created"
  | "follow_up_completed"
  | "file_added"
  | "customer_conversion"
  | "order_conversion";
export type FollowUpStatus = "scheduled" | "due" | "completed" | "cancelled" | "missed";

export interface LeadListItem {
  id: string;
  lead_number: string;
  display_name: string;
  organization_name: string | null;
  lead_type: LeadType;
  source: LeadSource;
  status: LeadStatus;
  priority: LeadPriority;
  estimated_value_minor: number | null;
  requested_date: string | null;
  party_size: number | null;
  assigned_staff_id: string | null;
  next_follow_up_at: string | null;
  last_contact_at: string | null;
  created_at: string;
}

export interface Lead {
  id: string;
  lead_number: string;
  lead_type: LeadType;
  display_name: string;
  organization_name: string | null;
  contact_name: string | null;
  phone_e164: string | null;
  email: string | null;
  source: LeadSource;
  campaign_reference: string | null;
  status: LeadStatus;
  priority: LeadPriority;
  estimated_value_minor: number | null;
  party_size: number | null;
  requested_date: string | null;
  requested_time: string | null;
  assigned_staff_id: string | null;
  next_follow_up_at: string | null;
  last_contact_at: string | null;
  won_customer_id: string | null;
  lost_reason: LostReason | null;
  description: string | null;
  qualification_notes: string | null;
  food_preferences: string | null;
  budget_notes: string | null;
  do_not_contact: boolean;
  converted_at: string | null;
  converted_by: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface LeadActivityEntry {
  id: string;
  lead_id: string;
  activity_type: LeadActivityType;
  summary: string;
  performed_by: string | null;
  occurred_at: string;
}

export interface LeadFollowUp {
  id: string;
  lead_id: string;
  assigned_to: string;
  scheduled_at: string;
  status: FollowUpStatus;
  completed_at: string | null;
  outcome: string | null;
  purpose: string | null;
  channel: string | null;
  completed_by: string | null;
}

export interface DuplicateLeadMatch {
  lead: LeadListItem;
  match_reasons: string[];
}

export interface ConversionPreview {
  lead: Lead;
  possible_customer_matches: CustomerListItem[];
  will_create_new_customer: boolean;
}

// --- Phase 6: Menu and Product Management ---
// Mirrors apps/api/app/menu/schemas.py.

export type FoodType = "vegetarian" | "non_vegetarian";
export type SpiceLevel = "mild" | "medium" | "hot" | "extra_hot";
export type AvailabilitySource =
  | "manual"
  | "inventory_derived"
  | "schedule"
  | "integration"
  | "override";

export interface MenuCategory {
  id: string;
  code: string;
  name: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  version: number;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  code: string;
  name: string;
  price_minor: number;
  sort_order: number;
  is_active: boolean;
  is_available: boolean;
  preparation_minutes: number | null;
  version: number;
}

export interface ProductListItem {
  id: string;
  product_code: string;
  name: string;
  display_name: string | null;
  category_id: string;
  food_type: FoodType;
  base_price_minor: number;
  is_active: boolean;
  is_available: boolean;
  is_featured: boolean;
  sort_order: number;
  image_storage_path: string | null;
}

export interface Product {
  id: string;
  product_code: string;
  barcode: string | null;
  category_id: string;
  name: string;
  display_name: string | null;
  slug: string;
  description: string | null;
  short_description: string | null;
  food_type: FoodType;
  is_jain_capable: boolean;
  is_vegan_capable: boolean;
  contains_egg: boolean;
  contains_dairy: boolean;
  contains_gluten: boolean;
  contains_nuts: boolean;
  contains_soy: boolean;
  contains_alcohol: boolean;
  spice_level: SpiceLevel | null;
  preparation_minutes: number | null;
  calories: number | null;
  base_price_minor: number;
  tax_category: string | null;
  is_active: boolean;
  is_available: boolean;
  availability_source: AvailabilitySource;
  manual_override_reason: string | null;
  dine_in_available: boolean;
  takeaway_available: boolean;
  delivery_available: boolean;
  image_storage_path: string | null;
  sort_order: number;
  is_featured: boolean;
  is_chef_recommended: boolean;
  version: number;
}

export interface ModifierGroup {
  id: string;
  name: string;
  min_select: number;
  max_select: number;
  is_required: boolean;
  sort_order: number;
  version: number;
}

export interface Modifier {
  id: string;
  name: string;
  default_price_minor: number;
  is_active: boolean;
  version: number;
}

export interface ModifierGroupItem {
  modifier_group_id: string;
  modifier_id: string;
  price_minor_override: number | null;
  sort_order: number;
  is_available: boolean;
}

export interface ProductModifierGroupMapping {
  product_id: string;
  modifier_group_id: string;
  sort_order: number;
}

export interface ProductImage {
  id: string;
  product_id: string;
  alt_text: string | null;
  sort_order: number;
  is_thumbnail: boolean;
  file_size_bytes: number;
  mime_type: string;
  signed_url: string;
}

// --- Phase 7: Orders and Order Lifecycle ---
// Mirrors apps/api/app/orders/schemas.py.

export type OrderSource =
  | "pos"
  | "walk_in"
  | "website"
  | "whatsapp"
  | "phone_call"
  | "zomato"
  | "swiggy"
  | "manual";
export type OrderType = "dine_in" | "takeaway" | "delivery";
export type OrderStatus =
  | "draft"
  | "pending_confirmation"
  | "confirmed"
  | "preparing"
  | "ready"
  | "completed"
  | "cancelled";
export type PaymentStatus = "pending" | "partial" | "paid" | "refunded" | "failed";
export type PaymentMethod = "cash" | "card" | "upi" | "online";
export type OrderDiscountType =
  | "flat"
  | "percentage"
  | "manual"
  | "coupon_placeholder"
  | "manager_override";
export type OrderChargeType = "packaging" | "delivery" | "service" | "other";
export type OrderTimelineEventType =
  | "created"
  | "assigned"
  | "status_changed"
  | "payment_updated"
  | "note_added"
  | "cancelled"
  | "completed"
  | "manual_edit";

export interface OrderItemModifierInput {
  modifier_id: string;
  quantity?: number;
}

export interface OrderItemInput {
  product_id: string;
  variant_id?: string | null;
  quantity?: number;
  modifiers?: OrderItemModifierInput[];
  kitchen_note?: string | null;
}

export interface OrderDiscountInput {
  discount_type: OrderDiscountType;
  amount_minor?: number | null;
  percentage?: number | null;
  reason: string;
  approved_by: string;
}

export interface OrderTaxInput {
  tax_name: string;
  rate_percentage?: number | null;
  amount_minor?: number | null;
}

export interface OrderChargeInput {
  charge_type: OrderChargeType;
  amount_minor: number;
}

export interface OrderCreateInput {
  customer_id?: string | null;
  lead_id?: string | null;
  source: OrderSource;
  order_type: OrderType;
  assigned_staff_id?: string | null;
  items: OrderItemInput[];
  discounts?: OrderDiscountInput[];
  taxes?: OrderTaxInput[];
  charges?: OrderChargeInput[];
  internal_notes?: string | null;
  customer_notes?: string | null;
  estimated_completion_time?: string | null;
  idempotency_key: string;
}

export interface OrderUpdateInput {
  customer_id?: string | null;
  lead_id?: string | null;
  internal_notes?: string | null;
  customer_notes?: string | null;
  estimated_completion_time?: string | null;
  expected_version?: number | null;
}

export interface OrderItemModifier {
  id: string;
  modifier_id: string | null;
  modifier_name_snapshot: string;
  price_minor_snapshot: number;
  quantity: number;
}

export interface OrderItem {
  id: string;
  order_id: string;
  product_id: string | null;
  variant_id: string | null;
  product_name_snapshot: string;
  variant_name_snapshot: string | null;
  product_code_snapshot: string | null;
  quantity: number;
  unit_price_minor: number;
  discount_minor: number;
  tax_minor: number;
  final_price_minor: number;
  kitchen_note: string | null;
  status: "active" | "cancelled";
  modifiers: OrderItemModifier[];
}

export interface OrderDiscount {
  id: string;
  discount_type: OrderDiscountType;
  amount_minor: number;
  percentage: number | null;
  reason: string;
  approved_by: string;
  created_by: string;
  created_at: string;
}

export interface OrderTax {
  id: string;
  tax_name: string;
  rate_percentage: number | null;
  amount_minor: number;
  created_at: string;
}

export interface OrderCharge {
  id: string;
  charge_type: OrderChargeType;
  amount_minor: number;
  created_at: string;
}

export interface OrderPayment {
  id: string;
  order_id: string;
  method: PaymentMethod;
  status: PaymentStatus;
  amount_minor: number;
  reference: string | null;
  notes: string | null;
  recorded_by: string;
  recorded_at: string;
  updated_at: string | null;
  updated_by: string | null;
}

export interface OrderNote {
  id: string;
  order_id: string;
  content: string;
  is_internal: boolean;
  created_by: string;
  created_at: string;
  updated_at: string | null;
  updated_by: string | null;
}

export interface OrderTimelineEntry {
  id: string;
  order_id: string;
  event_type: OrderTimelineEventType;
  summary: string;
  event_metadata: Record<string, unknown> | null;
  performed_by: string | null;
  occurred_at: string;
}

export interface OrderStatusHistoryEntry {
  id: string;
  order_id: string;
  previous_status: OrderStatus | null;
  new_status: OrderStatus;
  actor_id: string | null;
  reason: string | null;
  created_at: string;
}

export interface OrderAssignment {
  id: string;
  order_id: string;
  staff_id: string;
  assigned_by: string | null;
  assigned_at: string;
  unassigned_at: string | null;
}

export interface OrderListItem {
  id: string;
  order_number: string;
  customer_id: string | null;
  source: OrderSource;
  order_type: OrderType;
  status: OrderStatus;
  payment_status: PaymentStatus;
  assigned_staff_id: string | null;
  grand_total_minor: number;
  estimated_completion_time: string | null;
  created_at: string;
}

export interface OrderStatusCounts {
  pending_confirmation: number;
  preparing: number;
  ready: number;
  completed: number;
  cancelled: number;
}

export interface RecentOrderActivity {
  order_id: string;
  order_number: string;
  event_type: OrderTimelineEventType;
  summary: string;
  occurred_at: string;
}

export interface OrderDashboardStats {
  today_order_count: number;
  status_counts_today: OrderStatusCounts;
  revenue_today_minor: number;
  average_order_value_minor: number;
  recent_activity: RecentOrderActivity[];
}

export interface Order {
  id: string;
  order_number: string;
  customer_id: string | null;
  lead_id: string | null;
  source: OrderSource;
  order_type: OrderType;
  status: OrderStatus;
  payment_status: PaymentStatus;
  assigned_staff_id: string | null;
  subtotal_minor: number;
  discount_minor: number;
  tax_minor: number;
  charges_minor: number;
  grand_total_minor: number;
  internal_notes: string | null;
  customer_notes: string | null;
  estimated_completion_time: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
  discounts: OrderDiscount[];
  taxes: OrderTax[];
  charges: OrderCharge[];
}

// --- Phase 8: Inventory, Recipes & Stock Operations ---
// Mirrors apps/api/app/inventory/schemas.py. Every inventory quantity is an
// exact-decimal value on the wire (the backend's `Qty` type serializes
// Decimal as a string) — never parse these as JS numbers for arithmetic,
// only for display; the backend remains the sole calculation authority
// (CLAUDE.md section 5.1 / section 7).

export type UnitType = "weight" | "volume" | "count";
export type LocationType =
  | "kitchen"
  | "dry_store"
  | "chilled"
  | "frozen"
  | "bar"
  | "packaging"
  | "other";
export type SupplierStatus = "active" | "inactive" | "archived";
export type BatchStatus = "active" | "depleted" | "quarantined" | "expired" | "damaged";
export type MovementType =
  | "opening_balance"
  | "purchase_receipt"
  | "order_reservation"
  | "reservation_release"
  | "order_consumption"
  | "wastage"
  | "positive_adjustment"
  | "negative_adjustment"
  | "transfer_out"
  | "transfer_in"
  | "supplier_return"
  | "customer_return"
  | "stock_count_adjustment"
  | "reversal";
export type ReceiptStatus = "draft" | "posted" | "reversed";
export type TransferStatus = "draft" | "posted" | "reversed";
export type CountStatus = "draft" | "in_progress" | "submitted" | "approved" | "cancelled";
export type AdjustmentDirection = "increase" | "decrease";
export type AdjustmentReason =
  | "count_difference"
  | "data_correction"
  | "damaged"
  | "spoiled"
  | "missing"
  | "found"
  | "unit_conversion_correction";
export type WastageReason =
  | "preparation_waste"
  | "overproduction"
  | "spoilage"
  | "expiry"
  | "customer_return"
  | "quality_failure"
  | "accidental_damage"
  | "staff_error"
  | "other";
export type StockStatus =
  | "in_stock"
  | "low_stock"
  | "critical_stock"
  | "out_of_stock"
  | "reserved"
  | "quarantined"
  | "expired"
  | "damaged"
  | "under_count_review"
  | "discontinued";

// --- Units of measure ---

export interface UnitCreateInput {
  code: string;
  name: string;
  symbol: string;
  unit_type: UnitType;
  base_unit_id?: string | null;
  conversion_factor?: string;
  decimal_places?: number;
  sort_order?: number;
}

export interface UnitUpdateInput {
  name?: string | null;
  symbol?: string | null;
  conversion_factor?: string | null;
  decimal_places?: number | null;
  sort_order?: number | null;
  is_active?: boolean | null;
  expected_version?: number | null;
}

export interface UnitOfMeasure {
  id: string;
  code: string;
  name: string;
  symbol: string;
  unit_type: UnitType;
  base_unit_id: string | null;
  conversion_factor: string;
  decimal_places: number;
  is_active: boolean;
  sort_order: number;
  version: number;
}

// --- Categories / locations ---

export interface InventoryCategoryCreateInput {
  code: string;
  name: string;
  description?: string | null;
  sort_order?: number;
}

export interface InventoryCategoryUpdateInput {
  name?: string | null;
  description?: string | null;
  sort_order?: number | null;
  is_active?: boolean | null;
  expected_version?: number | null;
}

export interface InventoryCategory {
  id: string;
  code: string;
  name: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  version: number;
}

export interface StorageLocationCreateInput {
  code: string;
  name: string;
  description?: string | null;
  location_type?: LocationType;
  allows_negative_stock?: boolean;
  sort_order?: number;
}

export interface StorageLocationUpdateInput {
  name?: string | null;
  description?: string | null;
  location_type?: LocationType | null;
  allows_negative_stock?: boolean | null;
  sort_order?: number | null;
  is_active?: boolean | null;
  expected_version?: number | null;
}

export interface StorageLocation {
  id: string;
  code: string;
  name: string;
  description: string | null;
  location_type: LocationType;
  allows_negative_stock: boolean;
  is_active: boolean;
  sort_order: number;
  version: number;
}

// --- Suppliers ---

export interface SupplierCreateInput {
  supplier_code: string;
  name: string;
  contact_person?: string | null;
  phone_e164?: string | null;
  email?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string;
  supply_categories?: string[] | null;
  normal_lead_time_days?: number | null;
  payment_terms?: string | null;
  minimum_order_value_minor?: number | null;
  tax_identifier?: string | null;
  notes?: string | null;
}

export interface SupplierUpdateInput {
  name?: string | null;
  contact_person?: string | null;
  phone_e164?: string | null;
  email?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  supply_categories?: string[] | null;
  normal_lead_time_days?: number | null;
  payment_terms?: string | null;
  minimum_order_value_minor?: number | null;
  tax_identifier?: string | null;
  notes?: string | null;
  status?: SupplierStatus | null;
  expected_version?: number | null;
}

export interface Supplier {
  id: string;
  supplier_code: string;
  name: string;
  contact_person: string | null;
  phone_e164: string | null;
  email: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string;
  supply_categories: string[] | null;
  normal_lead_time_days: number | null;
  payment_terms: string | null;
  minimum_order_value_minor: number | null;
  tax_identifier: string | null;
  notes: string | null;
  status: SupplierStatus;
  version: number;
}

// --- Inventory items ---

export interface InventoryItemCreateInput {
  item_code?: string | null;
  name: string;
  description?: string | null;
  category_id: string;
  base_unit_id: string;
  default_purchase_unit_id?: string | null;
  purchase_conversion_factor?: string | null;
  default_location_id?: string | null;
  preferred_supplier_id?: string | null;
  alternative_supplier_id?: string | null;
  standard_cost_minor?: number | null;
  reorder_level?: string;
  reorder_quantity?: string;
  target_stock?: string;
  minimum_stock?: string;
  maximum_stock?: string | null;
  lead_time_days?: number | null;
  shelf_life_days?: number | null;
  is_perishable?: boolean;
  requires_batch_tracking?: boolean;
  requires_expiry_tracking?: boolean;
  allergen_flags?: string[] | null;
  brand?: string | null;
  supplier_item_code?: string | null;
  barcode?: string | null;
  storage_instructions?: string | null;
  notes?: string | null;
}

export interface InventoryItemUpdateInput {
  name?: string | null;
  description?: string | null;
  category_id?: string | null;
  default_purchase_unit_id?: string | null;
  purchase_conversion_factor?: string | null;
  default_location_id?: string | null;
  preferred_supplier_id?: string | null;
  alternative_supplier_id?: string | null;
  standard_cost_minor?: number | null;
  reorder_level?: string | null;
  reorder_quantity?: string | null;
  target_stock?: string | null;
  minimum_stock?: string | null;
  maximum_stock?: string | null;
  lead_time_days?: number | null;
  shelf_life_days?: number | null;
  is_perishable?: boolean | null;
  allergen_flags?: string[] | null;
  brand?: string | null;
  supplier_item_code?: string | null;
  barcode?: string | null;
  storage_instructions?: string | null;
  notes?: string | null;
  is_active?: boolean | null;
  expected_version?: number | null;
}

export interface InventoryItemListItem {
  id: string;
  item_code: string;
  name: string;
  category_id: string;
  current_stock: string;
  reserved_stock: string;
  reorder_level: string;
  stock_status: StockStatus;
  preferred_supplier_id: string | null;
  is_active: boolean;
  is_perishable: boolean;
  requires_batch_tracking: boolean;
  requires_expiry_tracking: boolean;
}

export interface InventoryItem {
  id: string;
  item_code: string;
  name: string;
  description: string | null;
  category_id: string;
  base_unit_id: string;
  default_purchase_unit_id: string | null;
  purchase_conversion_factor: string | null;
  default_location_id: string | null;
  preferred_supplier_id: string | null;
  alternative_supplier_id: string | null;
  current_stock: string;
  reserved_stock: string;
  reorder_level: string;
  reorder_quantity: string;
  target_stock: string;
  minimum_stock: string;
  maximum_stock: string | null;
  standard_cost_minor: number | null;
  latest_purchase_cost_minor: number | null;
  average_unit_cost_minor: number | null;
  lead_time_days: number | null;
  shelf_life_days: number | null;
  is_perishable: boolean;
  requires_batch_tracking: boolean;
  requires_expiry_tracking: boolean;
  allergen_flags: string[] | null;
  brand: string | null;
  supplier_item_code: string | null;
  barcode: string | null;
  storage_instructions: string | null;
  notes: string | null;
  stock_status: StockStatus;
  is_active: boolean;
  last_counted_at: string | null;
  last_received_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface StockBalance {
  id: string;
  inventory_item_id: string;
  storage_location_id: string;
  batch_id: string | null;
  on_hand_quantity: string;
  reserved_quantity: string;
  last_movement_at: string | null;
  last_counted_at: string | null;
}

export interface InventoryBatch {
  id: string;
  inventory_item_id: string;
  batch_code: string;
  storage_location_id: string;
  supplier_id: string | null;
  received_quantity: string;
  remaining_quantity: string;
  received_at: string;
  manufactured_at: string | null;
  expires_at: string | null;
  unit_cost_minor: number | null;
  status: BatchStatus;
}

export interface StockMovement {
  id: string;
  movement_number: string;
  inventory_item_id: string;
  storage_location_id: string;
  batch_id: string | null;
  movement_type: MovementType;
  quantity_delta: string;
  affects_on_hand: boolean;
  unit_cost_minor: number | null;
  total_value_minor: number | null;
  reference_type: string | null;
  reference_id: string | null;
  source_movement_id: string | null;
  reversed_by_movement_id: string | null;
  reversed_at: string | null;
  reason: string | null;
  performed_by: string | null;
  occurred_at: string;
  created_at: string;
}

// --- Receipts ---

export interface ReceiptCreateInput {
  supplier_id: string;
  storage_location_id: string;
  received_date: string;
  supplier_reference?: string | null;
  notes?: string | null;
}

export interface ReceiptItemCreateInput {
  inventory_item_id: string;
  purchase_unit_id: string;
  received_quantity: string;
  accepted_quantity: string;
  rejected_quantity?: string;
  unit_cost_minor: number;
  batch_code?: string | null;
  manufactured_at?: string | null;
  expires_at?: string | null;
  notes?: string | null;
}

export interface ReceiptReverseInput {
  reason: string;
}

export interface ReceiptItem {
  id: string;
  receipt_id: string;
  inventory_item_id: string;
  purchase_unit_id: string;
  received_quantity: string;
  accepted_quantity: string;
  rejected_quantity: string;
  base_quantity: string;
  unit_cost_minor: number;
  line_total_minor: number;
  batch_code: string | null;
  manufactured_at: string | null;
  expires_at: string | null;
  batch_id: string | null;
  notes: string | null;
}

export interface ReceiptListItem {
  id: string;
  receipt_number: string;
  supplier_id: string;
  storage_location_id: string;
  received_date: string;
  status: ReceiptStatus;
  total_value_minor: number;
  created_at: string;
}

export interface Receipt extends ReceiptListItem {
  supplier_reference: string | null;
  notes: string | null;
  posted_by: string | null;
  posted_at: string | null;
  reversed_by: string | null;
  reversed_at: string | null;
  reversal_reason: string | null;
  version: number;
  items: ReceiptItem[];
}

// --- Adjustments / wastage ---

export interface AdjustmentCreateInput {
  inventory_item_id: string;
  storage_location_id: string;
  batch_id?: string | null;
  direction: AdjustmentDirection;
  quantity: string;
  reason_category: AdjustmentReason;
  reason: string;
  approved_by?: string | null;
  idempotency_key?: string | null;
}

export interface Adjustment {
  id: string;
  adjustment_number: string;
  inventory_item_id: string;
  storage_location_id: string;
  batch_id: string | null;
  direction: AdjustmentDirection;
  quantity: string;
  reason_category: AdjustmentReason;
  reason: string;
  value_impact_minor: number | null;
  movement_id: string;
  recorded_by: string;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
}

export interface WastageCreateInput {
  inventory_item_id: string;
  storage_location_id: string;
  batch_id?: string | null;
  quantity: string;
  reason_category: WastageReason;
  reason: string;
  station?: string | null;
  related_order_id?: string | null;
  approved_by?: string | null;
  idempotency_key?: string | null;
}

export interface Wastage {
  id: string;
  wastage_number: string;
  inventory_item_id: string;
  storage_location_id: string;
  batch_id: string | null;
  quantity: string;
  reason_category: WastageReason;
  reason: string;
  station: string | null;
  related_order_id: string | null;
  value_impact_minor: number | null;
  movement_id: string;
  recorded_by: string;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
}

// --- Transfers ---

export interface TransferCreateInput {
  source_location_id: string;
  destination_location_id: string;
  notes?: string | null;
}

export interface TransferItemCreateInput {
  inventory_item_id: string;
  batch_id?: string | null;
  quantity: string;
  notes?: string | null;
}

export interface TransferReverseInput {
  reason: string;
}

export interface TransferItem {
  id: string;
  transfer_id: string;
  inventory_item_id: string;
  batch_id: string | null;
  destination_batch_id: string | null;
  quantity: string;
  notes: string | null;
}

export interface TransferListItem {
  id: string;
  transfer_number: string;
  source_location_id: string;
  destination_location_id: string;
  status: TransferStatus;
  created_at: string;
}

export interface Transfer extends TransferListItem {
  notes: string | null;
  requested_by: string;
  posted_by: string | null;
  posted_at: string | null;
  reversed_by: string | null;
  reversed_at: string | null;
  reversal_reason: string | null;
  version: number;
  items: TransferItem[];
}

// --- Stock counts ---

export interface StockCountCreateInput {
  storage_location_id: string;
  scheduled_date?: string | null;
  notes?: string | null;
}

export interface StockCountLineRecordInput {
  counted_quantity: string;
  reason?: string | null;
  notes?: string | null;
}

export interface StockCountLine {
  id: string;
  count_id: string;
  inventory_item_id: string;
  batch_id: string | null;
  system_quantity: string;
  counted_quantity: string | null;
  variance_quantity: string | null;
  variance_value_minor: number | null;
  reason: string | null;
  notes: string | null;
}

export interface StockCountListItem {
  id: string;
  count_number: string;
  storage_location_id: string;
  status: CountStatus;
  scheduled_date: string | null;
  created_at: string;
}

export interface StockCount extends StockCountListItem {
  started_at: string | null;
  completed_at: string | null;
  counted_by: string | null;
  submitted_by: string | null;
  submitted_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  cancelled_at: string | null;
  notes: string | null;
  version: number;
  lines: StockCountLine[];
}

// --- Recipes ---

export interface RecipeItemCreateInput {
  inventory_item_id: string;
  quantity_required: string;
  unit_id: string;
  waste_factor?: string;
  storage_location_id?: string | null;
  display_order?: number;
  notes?: string | null;
}

export interface RecipeCreateInput {
  product_id: string;
  variant_id?: string | null;
  yield_quantity?: string;
  yield_unit_id?: string | null;
  preparation_loss_percentage?: string;
  effective_from?: string | null;
  notes?: string | null;
  items?: RecipeItemCreateInput[];
}

export interface RecipeItem {
  id: string;
  recipe_id: string;
  inventory_item_id: string;
  quantity_required: string;
  unit_id: string;
  base_quantity: string;
  waste_factor: string;
  storage_location_id: string | null;
  display_order: number;
  notes: string | null;
}

export interface RecipeListItem {
  id: string;
  recipe_code: string;
  product_id: string;
  variant_id: string | null;
  yield_quantity: string;
  is_active: boolean;
  effective_from: string;
  effective_to: string | null;
}

export interface Recipe extends RecipeListItem {
  yield_unit_id: string | null;
  preparation_loss_percentage: string;
  notes: string | null;
  version: number;
  items: RecipeItem[];
}

export interface IngredientCost {
  recipe_item_id: string;
  inventory_item_id: string;
  inventory_item_name: string;
  base_quantity: string;
  effective_quantity: string;
  unit_cost_minor: number | null;
  cost_minor: number | null;
  cost_source: string | null;
}

export interface RecipeCost {
  recipe_id: string;
  ingredients: IngredientCost[];
  total_ingredient_cost_minor: number | null;
  effective_yield: string;
  cost_per_yield_minor: number | null;
  selling_price_minor: number | null;
  gross_margin_minor: number | null;
  gross_margin_percentage: string | null;
  missing_cost_item_names: string[];
}

// --- Balance verification ---

export interface BalanceDrift {
  inventory_item_id: string;
  storage_location_id: string;
  batch_id: string | null;
  projected_on_hand: string;
  ledger_on_hand: string;
  difference: string;
}

export interface BalanceRebuildResult {
  coordinates: number;
  created: number;
  updated: number;
}

// --- Dashboard ---

export interface InventoryDashboardStats {
  total_active_items: number;
  total_stock_value_minor: number;
  low_stock_count: number;
  critical_stock_count: number;
  out_of_stock_count: number;
  expiring_batches_7d: number;
  expired_batches: number;
  wastage_today_count: number;
  wastage_today_value_minor: number;
  receipts_today_count: number;
  transfers_in_progress: number;
  pending_stock_counts: number;
}

// --- Phase 9: Reservations, Tables & Calendar Management ---
// Mirrors apps/api/app/reservations/schemas.py.

export type ReservationSource = "phone" | "walk_in" | "online" | "whatsapp" | "staff";
export type ReservationStatus =
  | "requested"
  | "pending_review"
  | "needs_clarification"
  | "approved"
  | "rejected"
  | "confirmation_sending"
  | "confirmed"
  | "reminder_scheduled"
  | "arrived"
  | "seated"
  | "completed"
  | "no_show"
  | "cancelled_by_customer"
  | "cancelled_by_restaurant"
  | "expired";
export type CancellationSource = "customer" | "restaurant";
export type ReservationNoteType =
  | "internal"
  | "kitchen"
  | "guest_preference"
  | "allergy"
  | "special_occasion"
  | "accessibility"
  | "celebration"
  | "vip";
export type TableStatus =
  | "available"
  | "reserved"
  | "occupied"
  | "cleaning"
  | "blocked"
  | "maintenance"
  | "merged";
export type TableShape = "round" | "square" | "rectangle" | "oval" | "booth" | "bar" | "custom";
export type TableBlockType = "cleaning" | "maintenance" | "private_event" | "other";
export type WaitlistStatus = "waiting" | "notified" | "promoted" | "cancelled" | "expired";

export interface ReservationCreateInput {
  customer_id?: string | null;
  guest_name: string;
  phone_e164?: string | null;
  email?: string | null;
  party_size: number;
  reservation_date: string;
  start_time: string;
  end_time?: string | null;
  dining_area_id?: string | null;
  source: ReservationSource;
  special_requests?: string | null;
  deposit_required?: boolean;
  deposit_amount_minor?: number | null;
  idempotency_key: string;
}

export interface ReservationUpdateInput {
  customer_id?: string | null;
  guest_name?: string;
  phone_e164?: string | null;
  email?: string | null;
  party_size?: number;
  reservation_date?: string;
  start_time?: string;
  end_time?: string | null;
  dining_area_id?: string | null;
  special_requests?: string | null;
  deposit_required?: boolean;
  deposit_amount_minor?: number | null;
  expected_version?: number | null;
}

export interface ReservationTransitionInput {
  new_status: ReservationStatus;
  reason?: string | null;
}

export interface ReservationApprovalInput {
  approve: boolean;
  reason?: string | null;
}

export interface ReservationNoteInput {
  note_type?: ReservationNoteType;
  content: string;
  is_internal?: boolean;
}

export interface WalkInCreateInput {
  guest_name: string;
  phone_e164?: string | null;
  email?: string | null;
  party_size: number;
  dining_area_id?: string | null;
  special_requests?: string | null;
}

export interface Reservation {
  id: string;
  reservation_number: string;
  customer_id: string | null;
  guest_name: string;
  phone_e164: string | null;
  email: string | null;
  party_size: number;
  reservation_date: string;
  start_time: string;
  end_time: string | null;
  dining_area_id: string | null;
  status: ReservationStatus;
  source: ReservationSource;
  is_walk_in: boolean;
  special_requests: string | null;
  order_id: string | null;
  assigned_staff_id: string | null;
  approved_by: string | null;
  approved_at: string | null;
  rejected_by: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  arrived_at: string | null;
  seated_at: string | null;
  completed_at: string | null;
  no_show_at: string | null;
  cancelled_at: string | null;
  cancellation_source: CancellationSource | null;
  cancellation_reason: string | null;
  expires_at: string | null;
  deposit_required: boolean;
  deposit_amount_minor: number | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ReservationStatusHistoryEntry {
  id: string;
  reservation_id: string;
  previous_status: ReservationStatus | null;
  new_status: ReservationStatus;
  actor_id: string | null;
  reason: string | null;
  created_at: string;
}

export interface ReservationTimelineEntry {
  id: string;
  reservation_id: string;
  event_type: string;
  summary: string;
  event_metadata: Record<string, unknown> | null;
  performed_by: string | null;
  occurred_at: string;
}

export interface ReservationNote {
  id: string;
  reservation_id: string;
  note_type: ReservationNoteType;
  content: string;
  is_internal: boolean;
  created_by: string;
  created_at: string;
  updated_at: string | null;
  updated_by: string | null;
}

export interface DiningAreaCreateInput {
  code: string;
  name: string;
  description?: string | null;
  sort_order?: number;
  is_active?: boolean;
}

export interface DiningAreaUpdateInput {
  name?: string;
  description?: string | null;
  is_active?: boolean;
  expected_version?: number | null;
}

export interface DiningArea {
  id: string;
  code: string;
  name: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  version: number;
}

export interface RestaurantTableCreateInput {
  dining_area_id: string;
  table_number: string;
  capacity: number;
  minimum_capacity?: number | null;
  maximum_capacity?: number | null;
  shape?: TableShape;
  is_wheelchair_accessible?: boolean;
  is_temporary?: boolean;
  qr_identifier?: string | null;
  notes?: string | null;
  sort_order?: number;
}

export interface RestaurantTableUpdateInput {
  dining_area_id?: string;
  capacity?: number;
  minimum_capacity?: number | null;
  maximum_capacity?: number | null;
  shape?: TableShape;
  is_wheelchair_accessible?: boolean;
  is_temporary?: boolean;
  qr_identifier?: string | null;
  notes?: string | null;
  is_active?: boolean;
  expected_version?: number | null;
}

export interface TableStatusTransitionInput {
  new_status: TableStatus;
  reason?: string | null;
}

export interface TableMergeInput {
  secondary_table_ids: string[];
  reason?: string | null;
}

export interface TableSplitInput {
  reason?: string | null;
}

export interface TableBlockCreateInput {
  block_type: TableBlockType;
  starts_at: string;
  ends_at: string;
  reason?: string | null;
}

export interface RestaurantTable {
  id: string;
  dining_area_id: string;
  table_number: string;
  capacity: number;
  minimum_capacity: number | null;
  maximum_capacity: number | null;
  shape: TableShape;
  status: TableStatus;
  is_wheelchair_accessible: boolean;
  is_temporary: boolean;
  merged_with_table_id: string | null;
  qr_identifier: string | null;
  notes: string | null;
  is_active: boolean;
  sort_order: number;
  version: number;
}

export interface TableStatusHistoryEntry {
  id: string;
  restaurant_table_id: string;
  previous_status: TableStatus | null;
  new_status: TableStatus;
  reason: string | null;
  event_metadata: Record<string, unknown> | null;
  changed_by: string | null;
  created_at: string;
}

export interface TableBlock {
  id: string;
  restaurant_table_id: string;
  block_type: TableBlockType;
  starts_at: string;
  ends_at: string;
  reason: string | null;
  is_active: boolean;
  released_by: string | null;
  released_at: string | null;
}

export interface TableAssignInput {
  table_ids: string[];
}

export interface ReservationTableAssignment {
  id: string;
  reservation_id: string;
  restaurant_table_id: string;
  assigned_at: string;
  assigned_by: string | null;
  unassigned_at: string | null;
}

export interface WaitlistCreateInput {
  customer_id?: string | null;
  guest_name: string;
  phone_e164?: string | null;
  email?: string | null;
  party_size: number;
  dining_area_id?: string | null;
  priority?: number;
  estimated_wait_minutes?: number | null;
  notes?: string | null;
}

export interface WaitlistPromoteInput {
  reservation_id: string;
}

export interface WaitlistCancelInput {
  reason?: string | null;
}

export interface Waitlist {
  id: string;
  customer_id: string | null;
  guest_name: string;
  phone_e164: string | null;
  email: string | null;
  party_size: number;
  dining_area_id: string | null;
  priority: number;
  status: WaitlistStatus;
  requested_at: string;
  estimated_wait_minutes: number | null;
  notified_at: string | null;
  promoted_reservation_id: string | null;
  resolved_at: string | null;
  notes: string | null;
  version: number;
}

export interface CustomerReservationStats {
  lifetime_visit_count: number;
  no_show_count: number;
  cancellation_count: number;
  average_party_size: number | null;
  last_visit_at: string | null;
  preferred_dining_area_id: string | null;
  preferred_table_id: string | null;
  preferred_start_time: string | null;
}

export interface BusinessHoursUpdateInput {
  is_closed: boolean;
  opens_at?: string | null;
  closes_at?: string | null;
  closes_next_day?: boolean;
  break_starts_at?: string | null;
  break_ends_at?: string | null;
  notes?: string | null;
  expected_version?: number | null;
}

export interface BusinessHours {
  id: string;
  day_of_week: number;
  is_closed: boolean;
  opens_at: string | null;
  closes_at: string | null;
  closes_next_day: boolean;
  break_starts_at: string | null;
  break_ends_at: string | null;
  notes: string | null;
  version: number;
}

export interface HolidayCalendarCreateInput {
  holiday_date: string;
  name: string;
  is_closed?: boolean;
  opens_at?: string | null;
  closes_at?: string | null;
  notes?: string | null;
}

export interface HolidayCalendarUpdateInput {
  name?: string;
  is_closed?: boolean;
  opens_at?: string | null;
  closes_at?: string | null;
  notes?: string | null;
  expected_version?: number | null;
}

export interface HolidayCalendarEntry {
  id: string;
  holiday_date: string;
  name: string;
  is_closed: boolean;
  opens_at: string | null;
  closes_at: string | null;
  notes: string | null;
  version: number;
}

export interface ReservationPoliciesUpdateInput {
  deposit_required_by_default?: boolean;
  default_deposit_amount_minor?: number | null;
  advance_booking_limit_days?: number;
  minimum_notice_minutes?: number;
  cancellation_window_minutes?: number;
  no_show_grace_minutes?: number;
  buffer_before_minutes?: number;
  buffer_after_minutes?: number;
  default_minimum_party_size?: number;
  default_maximum_party_size?: number;
  large_party_threshold?: number;
  expected_version?: number | null;
}

export interface ReservationPolicies {
  id: string;
  deposit_required_by_default: boolean;
  default_deposit_amount_minor: number | null;
  advance_booking_limit_days: number;
  minimum_notice_minutes: number;
  cancellation_window_minutes: number;
  no_show_grace_minutes: number;
  buffer_before_minutes: number;
  buffer_after_minutes: number;
  default_minimum_party_size: number;
  default_maximum_party_size: number;
  large_party_threshold: number;
  version: number;
}

export interface ReservationSettingsUpdateInput {
  default_reservation_duration_minutes?: number;
  auto_assignment_enabled?: boolean;
  waitlist_enabled?: boolean;
  online_booking_enabled?: boolean;
  walk_in_enabled?: boolean;
  pending_request_expiry_minutes?: number | null;
  reminder_lead_time_minutes?: number | null;
  expected_version?: number | null;
}

export interface ReservationSettings {
  id: string;
  default_reservation_duration_minutes: number;
  auto_assignment_enabled: boolean;
  waitlist_enabled: boolean;
  online_booking_enabled: boolean;
  walk_in_enabled: boolean;
  pending_request_expiry_minutes: number | null;
  reminder_lead_time_minutes: number | null;
  version: number;
}

export interface ReservationOrderLinkInput {
  order_id: string;
}

export interface ReservationDashboardStats {
  target_date: string;
  total_count: number;
  upcoming_count: number;
  completed_count: number;
  cancelled_count: number;
  no_show_count: number;
  walk_in_count: number;
  average_party_size: number | null;
  average_dining_duration_minutes: number | null;
  conversion_rate: number | null;
  hourly_reservation_counts: Record<string, number>;
  dining_area_utilization: Record<string, number>;
  table_utilization: Record<string, number>;
}

// --- Phase 10: Communication Hub ---------------------------------------------

export type ConversationStatus =
  | "open"
  | "pending"
  | "waiting_on_customer"
  | "waiting_on_staff"
  | "snoozed"
  | "resolved"
  | "closed"
  | "spam";
export type ConversationPriority = "low" | "normal" | "high" | "urgent";
export type MessageDirection = "inbound" | "outbound" | "internal";
export type MessageType =
  | "text"
  | "email"
  | "sms"
  | "whatsapp"
  | "system_event"
  | "template"
  | "internal_note"
  | "attachment"
  | "reservation_update"
  | "order_update"
  | "feedback_request";
export type TemplateCategory =
  | "reservation_confirmation"
  | "reservation_reminder"
  | "reservation_cancellation"
  | "reservation_modification"
  | "waitlist_update"
  | "table_ready"
  | "order_confirmation"
  | "order_ready"
  | "order_cancellation"
  | "feedback_request"
  | "lead_follow_up"
  | "birthday"
  | "anniversary"
  | "general";
export type TemplateStatus = "draft" | "active" | "archived";
export type ScheduledMessagePurpose =
  | "reservation_reminder"
  | "feedback_request"
  | "lead_follow_up"
  | "manual";
export type ScheduledMessageStatus = "scheduled" | "processing" | "sent" | "cancelled" | "failed";
export type SuppressionDestinationType = "email" | "phone";
export type SuppressionReason =
  | "hard_bounce"
  | "spam_complaint"
  | "invalid_destination"
  | "manual_block"
  | "customer_request"
  | "unsubscribed";
export type SuppressionScope = "all" | "promotional_only";
export type CallDirection = "inbound" | "outbound";
export type CallOutcome = "connected" | "no_answer" | "voicemail" | "busy" | "wrong_number" | "other";

export interface CommunicationChannel {
  id: string;
  code: string;
  name: string;
  description: string | null;
  provider: string | null;
  default_sender_identity: string | null;
  is_enabled: boolean;
  inbound_enabled: boolean;
  outbound_enabled: boolean;
  requires_template: boolean;
  business_hours_restricted: boolean;
  rate_limit_per_minute: number | null;
  fallback_channel_id: string | null;
  sort_order: number;
}

export interface CommunicationChannelUpdateInput {
  is_enabled?: boolean;
  inbound_enabled?: boolean;
  outbound_enabled?: boolean;
  default_sender_identity?: string | null;
  rate_limit_per_minute?: number | null;
  fallback_channel_id?: string | null;
}

export interface ConversationCreateInput {
  channel_id: string;
  customer_id?: string | null;
  lead_id?: string | null;
  guest_name?: string | null;
  phone_e164?: string | null;
  email?: string | null;
  subject?: string | null;
  priority?: ConversationPriority;
  initial_message_body?: string | null;
}

export interface ConversationTransitionInput {
  target_status: ConversationStatus;
  reason?: string | null;
  snoozed_until?: string | null;
  spam_reason?: string | null;
}

export interface ConversationAssignInput {
  assignee_id?: string | null;
  reason?: string | null;
}

export interface ConversationPriorityInput {
  priority: ConversationPriority;
}

export interface Conversation {
  id: string;
  conversation_number: string;
  channel_id: string;
  customer_id: string | null;
  lead_id: string | null;
  guest_name: string | null;
  phone_e164: string | null;
  email: string | null;
  subject: string | null;
  status: ConversationStatus;
  priority: ConversationPriority;
  source: string;
  assigned_staff_id: string | null;
  last_inbound_at: string | null;
  last_outbound_at: string | null;
  last_activity_at: string | null;
  first_response_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  snoozed_until: string | null;
  unread_count: number;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface MessageCreateInput {
  body_text?: string | null;
  subject?: string | null;
  message_type?: MessageType;
  template_id?: string | null;
  template_variables?: Record<string, unknown> | null;
  recipient_reference?: string | null;
  idempotency_key: string;
}

export interface InternalNoteCreateInput {
  body_text: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  channel_id: string;
  direction: MessageDirection;
  message_type: MessageType;
  sender_reference: string | null;
  recipient_reference: string | null;
  subject: string | null;
  body_text: string | null;
  template_id: string | null;
  provider_message_id: string | null;
  reply_to_message_id: string | null;
  delivery_status: string;
  failure_code: string | null;
  failure_reason: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  failed_at: string | null;
  received_at: string | null;
  retry_count: number;
  created_by: string | null;
  created_at: string;
}

export interface MessageAttachment {
  id: string;
  message_id: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  upload_status: string;
  scan_status: string;
  created_at: string;
}

export interface ConversationTimelineEntry {
  entry_type: "message" | "status_change" | "assignment_change";
  occurred_at: string;
  payload: Record<string, unknown>;
}

export interface MessageTemplateCreateInput {
  name: string;
  code: string;
  channel_id: string;
  category: TemplateCategory;
  language?: string;
  subject?: string | null;
  body: string;
  variables?: string[];
  is_transactional?: boolean;
  effective_from?: string | null;
  effective_to?: string | null;
}

export interface MessageTemplateUpdateInput {
  name?: string;
  subject?: string | null;
  body?: string;
  variables?: string[];
  status?: TemplateStatus;
  is_transactional?: boolean;
  effective_from?: string | null;
  effective_to?: string | null;
  version: number;
}

export interface MessageTemplate {
  id: string;
  name: string;
  code: string;
  channel_id: string;
  category: TemplateCategory;
  language: string;
  subject: string | null;
  body: string;
  variables: string[];
  status: TemplateStatus;
  provider_template_id: string | null;
  is_transactional: boolean;
  effective_from: string | null;
  effective_to: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface TemplatePreviewInput {
  variables: Record<string, unknown>;
}

export interface TemplatePreviewOutput {
  subject: string | null;
  body: string;
}

export interface ScheduledMessageCreateInput {
  purpose: ScheduledMessagePurpose;
  template_id?: string | null;
  conversation_id?: string | null;
  customer_id?: string | null;
  lead_id?: string | null;
  channel_id: string;
  recipient_reference: string;
  scheduled_for: string;
  timezone?: string;
  template_variables?: Record<string, unknown> | null;
  idempotency_key: string;
}

export interface ScheduledMessage {
  id: string;
  purpose: ScheduledMessagePurpose;
  template_id: string | null;
  conversation_id: string | null;
  customer_id: string | null;
  lead_id: string | null;
  channel_id: string;
  recipient_reference: string;
  scheduled_for: string;
  timezone: string;
  status: ScheduledMessageStatus;
  cancelled_at: string | null;
  attempt_count: number;
  last_error: string | null;
  result_message_id: string | null;
  created_at: string;
}

export interface CommunicationPreferenceUpdateInput {
  preferred_channel_id?: string | null;
  allow_transactional_email?: boolean;
  allow_transactional_sms?: boolean;
  allow_transactional_whatsapp?: boolean;
  allow_promotional_email?: boolean;
  allow_promotional_sms?: boolean;
  allow_promotional_whatsapp?: boolean;
  do_not_contact?: boolean;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  language_preference?: string;
}

export interface CommunicationPreference {
  id: string;
  customer_id: string;
  preferred_channel_id: string | null;
  allow_transactional_email: boolean;
  allow_transactional_sms: boolean;
  allow_transactional_whatsapp: boolean;
  allow_promotional_email: boolean;
  allow_promotional_sms: boolean;
  allow_promotional_whatsapp: boolean;
  do_not_contact: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  language_preference: string;
}

export interface CommunicationConsentCreateInput {
  customer_id: string;
  consent_type: string;
  consent_given: boolean;
  source: string;
  consent_version?: string | null;
}

export interface CommunicationConsent {
  id: string;
  customer_id: string;
  consent_type: string;
  consent_given: boolean;
  source: string;
  consent_version: string | null;
  actor_id: string | null;
  created_at: string;
}

export interface CommunicationSuppressionCreateInput {
  destination_type: SuppressionDestinationType;
  destination_value: string;
  reason: SuppressionReason;
  scope?: SuppressionScope;
  suppressed_until?: string | null;
  customer_id?: string | null;
  notes?: string | null;
}

export interface CommunicationSuppression {
  id: string;
  destination_type: SuppressionDestinationType;
  destination_value: string;
  reason: SuppressionReason;
  scope: SuppressionScope;
  suppressed_until: string | null;
  is_active: boolean;
  customer_id: string | null;
  notes: string | null;
  lifted_at: string | null;
  created_at: string;
}

export interface ManualCallLogCreateInput {
  customer_id?: string | null;
  lead_id?: string | null;
  conversation_id?: string | null;
  direction: CallDirection;
  started_at: string;
  ended_at?: string | null;
  outcome: CallOutcome;
  notes?: string | null;
  follow_up_required?: boolean;
  related_reservation_id?: string | null;
  related_order_id?: string | null;
}

export interface ManualCallLog {
  id: string;
  customer_id: string | null;
  lead_id: string | null;
  conversation_id: string | null;
  staff_user_id: string;
  direction: CallDirection;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  outcome: CallOutcome;
  notes: string | null;
  follow_up_required: boolean;
  created_at: string;
}

export interface CommunicationAnalytics {
  open_conversations: number;
  unread_conversations: number;
  waiting_on_staff: number;
  waiting_on_customer: number;
  resolved_today: number;
  average_first_response_seconds: number | null;
  average_resolution_seconds: number | null;
  messages_by_channel: Record<string, number>;
  inbound_count: number;
  outbound_count: number;
  delivery_rate: number | null;
  failure_rate: number | null;
  suppression_count: number;
}

export interface CustomerCommunicationStats {
  open_conversation_count: number;
  total_inbound_messages: number;
  total_outbound_messages: number;
  last_contact_at: string | null;
  preferred_channel_id: string | null;
  average_response_seconds: number | null;
  unresolved_conversation_count: number;
}

// --- Phase 10: Operational Tasks ---------------------------------------------

export type TaskSource =
  | "manual"
  | "reservation_followup"
  | "order_issue"
  | "lead_followup"
  | "inventory_alert"
  | "system"
  | "recurring";
export type TaskPriority = "low" | "normal" | "high" | "urgent";
export type TaskStatus = "open" | "in_progress" | "blocked" | "completed" | "cancelled";
export type TaskRelatedType =
  | "customer"
  | "lead"
  | "order"
  | "reservation"
  | "conversation"
  | "inventory_item";

export interface RecurrenceRule {
  frequency: "daily" | "weekly" | "monthly";
  interval?: number;
  days_of_week?: number[] | null;
  end_date?: string | null;
}

export interface TaskCreateInput {
  title: string;
  description?: string | null;
  source?: TaskSource;
  priority?: TaskPriority;
  due_at?: string | null;
  assigned_staff_id?: string | null;
  assigned_department_id?: string | null;
  related_type?: TaskRelatedType | null;
  related_id?: string | null;
  is_recurring_template?: boolean;
  recurrence_rule?: RecurrenceRule | null;
  idempotency_key?: string | null;
}

export interface TaskUpdateInput {
  title?: string;
  description?: string | null;
  priority?: TaskPriority;
  due_at?: string | null;
  version: number;
}

export interface TaskTransitionInput {
  target_status: TaskStatus;
  reason?: string | null;
  completion_notes?: string | null;
  blocked_reason?: string | null;
}

export interface TaskAssignInput {
  assigned_staff_id?: string | null;
  assigned_department_id?: string | null;
  reason?: string | null;
}

export interface Task {
  id: string;
  task_number: string;
  title: string;
  description: string | null;
  source: TaskSource;
  priority: TaskPriority;
  status: TaskStatus;
  due_at: string | null;
  assigned_staff_id: string | null;
  assigned_department_id: string | null;
  completed_at: string | null;
  completed_by: string | null;
  completion_notes: string | null;
  blocked_reason: string | null;
  related_type: TaskRelatedType | null;
  related_id: string | null;
  is_recurring_template: boolean;
  recurrence_rule: RecurrenceRule | null;
  parent_task_id: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

// --- Phase 10: Notifications --------------------------------------------------

export type NotificationPriority = "low" | "normal" | "high" | "urgent";

export interface Notification {
  id: string;
  recipient_staff_id: string;
  notification_type: string;
  title: string;
  body: string | null;
  priority: NotificationPriority;
  record_type: string | null;
  record_id: string | null;
  read_at: string | null;
  dismissed_at: string | null;
  actioned_at: string | null;
  created_at: string;
}

export interface NotificationBroadcastInput {
  recipient_staff_ids: string[];
  title: string;
  body?: string | null;
  priority?: NotificationPriority;
}
