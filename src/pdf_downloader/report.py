from enum import Enum

OrgType = Enum(
  "OrgType",
  [
    "OTHER",
    "FOUNDATION",
    "GOVERNMENT",
    "SUBSIDIARY",
    "COOPERATIVE",
    "PARTNERSHIP",
    "PRIVATE_COMPANY",
    "PUBLIC_INSTITUTION",
    "STATE-OWNED_COMPANY",
    "NON-PROFIT_ORGANIZATION",
  ],
)

Sector = Enum(
  "Sector",
  [
    "TOYS",
    "MEDIA",
    "OTHER",
    "ENERGY",
    "MINING",
    "TOBACCO",
    "AVIATION",
    "RAILROAD",
    "CHEMICALS",
    "COMPUTERS",
    "EQUIPMENT",
    "LOGISTICS",
    "RETAILERS",
    "AUTOMOTIVE",
    "AGRICULTURE",
    "REAL ESTATE",
    "CONSTRUCTION",
    "UNIVERSITIES",
    "CONGLOMERATES",
    "PUBLIC AGENCY",
    "METALS PRODUCTS",
    "TOURISM/LEISURE",
    "WATER UTILITIES",
    "ENERGY UTILITIES",
    "WASTE MANAGEMENT",
    "CONSUMER DURABLES",
    "FINANCIAL SERVICES",
    "TELECOMMUNICATIONS",
    "COMMERCIAL SERVICES",
    "HEALTHCARE PRODUCTS",
    "HEALTHCARE SERVICES",
    "TECHNOLOGY HARDWARE",
    "TEXTILES AND APPAREL",
    "NON-PROFIT / SERVICES",
    "CONSTRUCTION MATERIALS",
    "FOREST AND PAPER PRODUCTS",
    "FOOD AND BEVERAGE PRODUCTS",
    "HOUSEHOLD AND PERSONAL PRODUCTS",
  ],
)


class Report:
  """Data model for a report"""

  main_url: str | None = None
  fallback_url: str | None = None
  """
    # featured: bool = False
    # name: str = ""
    # is_gold: bool = False
    # org_type: OrgType = OrgType.OTHER
    # size: str | None = ""  # Small/Medium, Multinational, Large, None
    # is_listed: bool = False
    # sector: Sector = Sector.OTHER
    # country: str = ""
    # country_status: str = ""
    # region: str = ""
    # date_added: date = datetime.today().date()
    # title: str = ""
    # publication_year: int = datetime.today().year
    # is_integrated: bool = False
    # type: str = ""
    # adherence: str = ""
  """

  def __init__(self, id: int, main_url: str, fallback_url: str):
    self.ID: int = id
    self.main_url = main_url
    self.fallback_url = fallback_url
