from app.db.models.attendance_correction import AttendanceCorrection
from app.db.models.attendance_record import AttendanceRecord
from app.db.models.audit_event import AuditEvent
from app.db.models.business_hours import BusinessHours
from app.db.models.communication_channel import CommunicationChannel
from app.db.models.communication_consent import CommunicationConsent
from app.db.models.communication_preference import CommunicationPreference
from app.db.models.communication_suppression import CommunicationSuppression
from app.db.models.conversation import Conversation
from app.db.models.conversation_assignment import ConversationAssignment
from app.db.models.conversation_link import ConversationLink
from app.db.models.conversation_status_history import ConversationStatusHistory
from app.db.models.customer import Customer
from app.db.models.customer_address import CustomerAddress
from app.db.models.customer_consent import CustomerConsent
from app.db.models.customer_merge_event import CustomerMergeEvent
from app.db.models.customer_note import CustomerNote
from app.db.models.customer_preference import CustomerPreference
from app.db.models.customer_tag import CustomerTag
from app.db.models.department import Department
from app.db.models.dining_area import DiningArea
from app.db.models.holiday_calendar import HolidayCalendar
from app.db.models.inbound_webhook_event import InboundWebhookEvent
from app.db.models.inventory_batch import InventoryBatch
from app.db.models.inventory_category import InventoryCategory
from app.db.models.inventory_item import InventoryItem
from app.db.models.job_record import JobRecord
from app.db.models.knowledge_acknowledgement import KnowledgeAcknowledgement
from app.db.models.knowledge_article import KnowledgeArticle
from app.db.models.knowledge_article_relation import KnowledgeArticleRelation
from app.db.models.knowledge_article_tag import KnowledgeArticleTag
from app.db.models.knowledge_article_version import KnowledgeArticleVersion
from app.db.models.knowledge_assignment import KnowledgeAssignment
from app.db.models.knowledge_attachment import KnowledgeAttachment
from app.db.models.knowledge_category import KnowledgeCategory
from app.db.models.knowledge_review import KnowledgeReview
from app.db.models.knowledge_visibility_rule import KnowledgeVisibilityRule
from app.db.models.lead import Lead
from app.db.models.lead_activity import LeadActivity
from app.db.models.lead_follow_up import LeadFollowUp
from app.db.models.lead_status_history import LeadStatusHistory
from app.db.models.leave_request import LeaveRequest
from app.db.models.leave_type import LeaveType
from app.db.models.manual_call_log import ManualCallLog
from app.db.models.menu_category import MenuCategory
from app.db.models.message import Message
from app.db.models.message_attachment import MessageAttachment
from app.db.models.message_delivery_attempt import MessageDeliveryAttempt
from app.db.models.message_status_history import MessageStatusHistory
from app.db.models.message_template import MessageTemplate
from app.db.models.modifier import Modifier
from app.db.models.modifier_group import ModifierGroup
from app.db.models.modifier_group_item import ModifierGroupItem
from app.db.models.notification import Notification
from app.db.models.order import Order
from app.db.models.order_assignment import OrderAssignment
from app.db.models.order_charge import OrderCharge
from app.db.models.order_discount import OrderDiscount
from app.db.models.order_inventory_state import OrderInventoryState
from app.db.models.order_item import OrderItem
from app.db.models.order_item_modifier import OrderItemModifier
from app.db.models.order_note import OrderNote
from app.db.models.order_payment import OrderPayment
from app.db.models.order_source_metadata import OrderSourceMetadata
from app.db.models.order_status_history import OrderStatusHistory
from app.db.models.order_tax import OrderTax
from app.db.models.order_timeline import OrderTimeline
from app.db.models.outbox_event import OutboxEvent
from app.db.models.performance_review import PerformanceReview
from app.db.models.performance_review_goal import PerformanceReviewGoal
from app.db.models.permission import Permission
from app.db.models.product import Product
from app.db.models.product_image import ProductImage
from app.db.models.product_modifier_group import ProductModifierGroup
from app.db.models.product_variant import ProductVariant
from app.db.models.provider_status_event import ProviderStatusEvent
from app.db.models.recipe import Recipe, RecipeItem
from app.db.models.reservation import Reservation
from app.db.models.reservation_note import ReservationNote
from app.db.models.reservation_policy import ReservationPolicies
from app.db.models.reservation_setting import ReservationSettings
from app.db.models.reservation_status_history import ReservationStatusHistory
from app.db.models.reservation_table_assignment import ReservationTableAssignment
from app.db.models.reservation_tag import ReservationTag
from app.db.models.reservation_tag_link import ReservationTagLink
from app.db.models.reservation_timeline import ReservationTimeline
from app.db.models.reservation_waitlist import ReservationWaitlist
from app.db.models.restaurant_table import RestaurantTable
from app.db.models.role import Role
from app.db.models.role_permission import RolePermission
from app.db.models.scheduled_message import ScheduledMessage
from app.db.models.shift_change_request import ShiftChangeRequest
from app.db.models.shift_template import ShiftTemplate
from app.db.models.skill import Skill
from app.db.models.staff_availability_window import StaffAvailabilityWindow
from app.db.models.staff_certification import StaffCertification
from app.db.models.staff_disciplinary_record import StaffDisciplinaryRecord
from app.db.models.staff_document import StaffDocument
from app.db.models.staff_employment_profile import StaffEmploymentProfile
from app.db.models.staff_invitation import StaffInvitation
from app.db.models.staff_reporting_history import StaffReportingHistory
from app.db.models.staff_role import StaffRole
from app.db.models.staff_shift import StaffShift
from app.db.models.staff_skill import StaffSkill
from app.db.models.staff_status_history import StaffStatusHistory
from app.db.models.staff_transition_plan import StaffTransitionPlan
from app.db.models.staff_transition_step import StaffTransitionStep
from app.db.models.staff_transition_template import StaffTransitionTemplate
from app.db.models.staff_transition_template_step import StaffTransitionTemplateStep
from app.db.models.staff_user import StaffUser
from app.db.models.stock_adjustment import StockAdjustment
from app.db.models.stock_balance import StockBalance
from app.db.models.stock_count import StockCount, StockCountLine
from app.db.models.stock_movement import StockMovement
from app.db.models.stock_receipt import StockReceipt, StockReceiptItem
from app.db.models.stock_transfer import StockTransfer, StockTransferItem
from app.db.models.storage_location import StorageLocation
from app.db.models.supplier import Supplier
from app.db.models.table_block import TableBlock
from app.db.models.table_status_history import TableStatusHistory
from app.db.models.tag import Tag
from app.db.models.task_assignment import TaskAssignment
from app.db.models.task_record import TaskRecord
from app.db.models.task_status_history import TaskStatusHistory
from app.db.models.training_assignment import TrainingAssignment
from app.db.models.training_attempt import TrainingAttempt
from app.db.models.training_course import TrainingCourse
from app.db.models.unit_of_measure import UnitOfMeasure
from app.db.models.wastage_record import WastageRecord

__all__ = [
    "AttendanceCorrection",
    "AttendanceRecord",
    "AuditEvent",
    "BusinessHours",
    "CommunicationChannel",
    "CommunicationConsent",
    "CommunicationPreference",
    "CommunicationSuppression",
    "Conversation",
    "ConversationAssignment",
    "ConversationLink",
    "ConversationStatusHistory",
    "Customer",
    "CustomerAddress",
    "CustomerConsent",
    "CustomerMergeEvent",
    "CustomerNote",
    "CustomerPreference",
    "CustomerTag",
    "Department",
    "DiningArea",
    "HolidayCalendar",
    "InboundWebhookEvent",
    "InventoryBatch",
    "InventoryCategory",
    "InventoryItem",
    "JobRecord",
    "KnowledgeAcknowledgement",
    "KnowledgeArticle",
    "KnowledgeArticleRelation",
    "KnowledgeArticleTag",
    "KnowledgeArticleVersion",
    "KnowledgeAssignment",
    "KnowledgeAttachment",
    "KnowledgeCategory",
    "KnowledgeReview",
    "KnowledgeVisibilityRule",
    "Lead",
    "LeadActivity",
    "LeadFollowUp",
    "LeadStatusHistory",
    "LeaveRequest",
    "LeaveType",
    "ManualCallLog",
    "MenuCategory",
    "Message",
    "MessageAttachment",
    "MessageDeliveryAttempt",
    "MessageStatusHistory",
    "MessageTemplate",
    "Modifier",
    "ModifierGroup",
    "ModifierGroupItem",
    "Notification",
    "Order",
    "OrderAssignment",
    "OrderCharge",
    "OrderDiscount",
    "OrderInventoryState",
    "OrderItem",
    "OrderItemModifier",
    "OrderNote",
    "OrderPayment",
    "OrderSourceMetadata",
    "OrderStatusHistory",
    "OrderTax",
    "OrderTimeline",
    "OutboxEvent",
    "PerformanceReview",
    "PerformanceReviewGoal",
    "Permission",
    "Product",
    "ProductImage",
    "ProductModifierGroup",
    "ProductVariant",
    "ProviderStatusEvent",
    "Recipe",
    "RecipeItem",
    "Reservation",
    "ReservationNote",
    "ReservationPolicies",
    "ReservationSettings",
    "ReservationStatusHistory",
    "ReservationTableAssignment",
    "ReservationTag",
    "ReservationTagLink",
    "ReservationTimeline",
    "ReservationWaitlist",
    "RestaurantTable",
    "Role",
    "RolePermission",
    "ScheduledMessage",
    "ShiftChangeRequest",
    "ShiftTemplate",
    "Skill",
    "StaffAvailabilityWindow",
    "StaffCertification",
    "StaffDisciplinaryRecord",
    "StaffDocument",
    "StaffEmploymentProfile",
    "StaffInvitation",
    "StaffReportingHistory",
    "StaffRole",
    "StaffShift",
    "StaffSkill",
    "StaffStatusHistory",
    "StaffTransitionPlan",
    "StaffTransitionStep",
    "StaffTransitionTemplate",
    "StaffTransitionTemplateStep",
    "StaffUser",
    "StockAdjustment",
    "StockBalance",
    "StockCount",
    "StockCountLine",
    "StockMovement",
    "StockReceipt",
    "StockReceiptItem",
    "StockTransfer",
    "StockTransferItem",
    "StorageLocation",
    "Supplier",
    "TableBlock",
    "TableStatusHistory",
    "Tag",
    "TaskAssignment",
    "TaskRecord",
    "TaskStatusHistory",
    "TrainingAssignment",
    "TrainingAttempt",
    "TrainingCourse",
    "UnitOfMeasure",
    "WastageRecord",
]
