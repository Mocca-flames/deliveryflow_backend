"""
Pydantic schemas for SADC document generation.
"""
from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    tel: str | None = None
    fax: str | None = None
    cell: str | None = None
    email: str | None = None


class Party(BaseModel):
    legalName: str
    logoUrl: str | None = None
    vatNumber: str | None = None
    companyRegistrationNumber: str | None = None
    postalAddress: str | None = None
    physicalAddress: str | None = None
    city: str | None = None
    province: str | None = None
    postalCode: str | None = None
    country: str = "South Africa"
    contact: ContactInfo = Field(default_factory=ContactInfo)
    contactPersonName: str | None = None


class LineItem(BaseModel):
    itemCode: str | None = None
    description: str
    detailLines: list[str] = Field(default_factory=list)
    quantity: float
    unit: str = "unit"
    unitPrice: float
    currency: str = "ZAR"
    discountPercent: float = 0
    vatPercent: float | None = None
    exclTotal: float = 0
    inclTotal: float = 0


class DocumentTotals(BaseModel):
    subTotalExcl: float
    totalDiscount: float = 0
    totalVat: float | None = None
    grandTotal: float
    balanceDue: float
    amountPaid: float | None = None
    currency: str = "ZAR"


class BankingDetails(BaseModel):
    bankName: str
    accountHolder: str
    accountNumber: str
    accountType: str | None = None
    branchName: str | None = None
    branchCode: str | None = None
    swiftCode: str | None = None


class DocumentFooter(BaseModel):
    thankYouMessage: str | None = None
    termsNotes: str | None = None


class DocumentMeta(BaseModel):
    documentType: str  # "Tax Invoice" | "Invoice" | "Quotation" | "Proforma Invoice" etc.
    documentNumber: str
    reference: str | None = None
    date: str
    dueDate: str | None = None
    salesRep: str | None = None
    overallDiscountPercent: float = 0
    pageInfo: str | None = None
    statusStamp: str | None = None  # "PAID" | "OVERDUE" | "DRAFT" | "CANCELLED"
    currency: str = "ZAR"  # Primary document currency


class ThemeTokens(BaseModel):
    primaryColor: str = "#1a3a5c"
    secondaryColor: str = "#2c5aa0"
    textColor: str = "#333333"
    lightBg: str = "#f9f9f9"
    borderColor: str = "#dddddd"
    fontFamily: str = "Georgia, 'Times New Roman', serif"
    fontSize: str = "11pt"


class TemplateConfig(BaseModel):
    logoPosition: str = "left"  # "left" | "right"
    partyOrder: str = "issuerLeft"  # "issuerLeft" | "recipientLeft"
    showVatColumn: bool = True
    showDualAddress: bool = True
    theme: ThemeTokens = Field(default_factory=ThemeTokens)


class SadcDocumentRequest(BaseModel):
    """Request body for SADC document PDF generation."""
    meta: DocumentMeta
    issuer: Party
    recipient: Party
    lineItems: list[LineItem]
    totals: DocumentTotals
    banking: BankingDetails | None = None
    footer: DocumentFooter | None = None
    templateConfig: TemplateConfig = Field(default_factory=TemplateConfig)
    templateId: str = "classic"  # "classic" | "modern"
