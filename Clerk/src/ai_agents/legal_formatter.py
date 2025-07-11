"""
Legal Document Formatter
Provides professional formatting for legal motions including case captions, signature blocks, and proper spacing
"""

import re
from typing import List, Dict, Any
from datetime import datetime


class LegalFormatter:
    """Formats legal documents with proper structure and professional appearance"""

    def __init__(self):
        """Initialize legal formatter with standard settings"""
        self.line_width = 80
        self.double_space_sections = False  # Single space for most courts

    def format_case_caption(
        self,
        case_name: str,
        case_number: str,
        court_name: str = "IN THE CIRCUIT COURT FOR THE ELEVENTH JUDICIAL CIRCUIT",
        court_location: str = "IN AND FOR MIAMI-DADE COUNTY, FLORIDA",
        plaintiff_name: str = None,
        defendant_names: List[str] = None,
    ) -> str:
        """Format a proper case caption for court filings"""

        caption = ""

        # Court header (centered)
        caption += self._center_text(court_name) + "\n"
        caption += self._center_text(court_location) + "\n\n"

        # Case style with proper alignment
        if plaintiff_name and defendant_names:
            # Left side - Plaintiff
            caption += f"{plaintiff_name},\n"
            caption += "\n        Plaintiff,\n"
            caption += "\nvs.\n\n"

            # Defendants
            for i, defendant in enumerate(defendant_names):
                caption += f"{defendant}"
                if i < len(defendant_names) - 1:
                    caption += ",\n"
                else:
                    caption += ",\n"
            caption += "\n        Defendants.\n"
        else:
            # Use provided case name
            caption += f"{case_name}\n"

        # Case number (right-aligned)
        caption += f"\n{' ' * 40}CASE NO.: {case_number}\n"

        # Divider
        caption += "_" * 70 + "/\n\n"

        return caption

    def format_motion_title(self, motion_title: str, is_emergency: bool = False) -> str:
        """Format the motion title with proper emphasis"""

        title = ""

        if is_emergency:
            title += "EMERGENCY\n\n"

        # Center and capitalize the motion title
        title += self._center_text(motion_title.upper()) + "\n\n"

        return title

    def format_signature_block(
        self,
        attorney_name: str,
        bar_number: str,
        firm_name: str,
        address: List[str],
        phone: str,
        email: str,
        attorney_for: str = "Plaintiff",
    ) -> str:
        """Format a professional signature block"""

        sig_block = "\n" + " " * 40 + "Respectfully submitted,\n\n"
        sig_block += " " * 40 + f"{firm_name.upper()}\n"
        sig_block += " " * 40 + f"Attorneys for {attorney_for}\n\n"
        sig_block += " " * 40 + f"/s/ {attorney_name}\n"
        sig_block += " " * 40 + "_" * 30 + "\n"
        sig_block += " " * 40 + f"{attorney_name}, Esq.\n"
        sig_block += " " * 40 + f"Florida Bar No.: {bar_number}\n"

        for line in address:
            sig_block += " " * 40 + f"{line}\n"

        sig_block += " " * 40 + f"Telephone: {phone}\n"
        sig_block += " " * 40 + f"Email: {email}\n"

        return sig_block

    def format_certificate_of_service(
        self,
        service_date: datetime = None,
        service_method: str = "electronic mail",
        served_parties: List[Dict[str, str]] = None,
    ) -> str:
        """Format a certificate of service"""

        if not service_date:
            service_date = datetime.now()

        cert = "\n\nCERTIFICATE OF SERVICE\n\n"

        cert += f"I HEREBY CERTIFY that on {service_date.strftime('%B %d, %Y')}, "
        cert += (
            f"a true and correct copy of the foregoing was served by {service_method} "
        )
        cert += "to the following:\n\n"

        if served_parties:
            for party in served_parties:
                cert += f"{party.get('name', '')}\n"
                cert += f"{party.get('firm', '')}\n"
                cert += f"{party.get('address', '')}\n"
                cert += f"{party.get('email', '')}\n"
                cert += f"Attorneys for {party.get('represents', 'Defendant')}\n\n"

        cert += " " * 40 + "/s/ [Attorney Name]\n"
        cert += " " * 40 + "_" * 30 + "\n"
        cert += " " * 40 + "Attorney\n"

        return cert

    def format_wherefore_clause(
        self,
        party_name: str,
        relief_requested: List[str],
        include_costs: bool = True,
        include_further_relief: bool = True,
    ) -> str:
        """Format a WHEREFORE prayer for relief clause"""

        wherefore = f"\nWHEREFORE, {party_name} respectfully requests that this Honorable Court:\n\n"

        # Add numbered relief items
        for i, relief in enumerate(relief_requested, 1):
            wherefore += f"{i}. {relief};\n\n"

        # Add standard requests
        next_num = len(relief_requested) + 1

        if include_costs:
            wherefore += (
                f"{next_num}. Award {party_name} costs and attorney's fees;\n\n"
            )
            next_num += 1

        if include_further_relief:
            wherefore += f"{next_num}. Grant such other and further relief as this Court deems just and equitable.\n"

        return wherefore

    def format_legal_argument(
        self, argument_number: str, argument_heading: str, argument_text: str
    ) -> str:
        """Format a legal argument section with proper structure"""

        formatted = f"\n{argument_number}. {argument_heading}\n\n"

        # Process paragraphs
        paragraphs = argument_text.split("\n\n")
        for para in paragraphs:
            if para.strip():
                # Indent first line of each paragraph
                formatted += "        " + para.strip() + "\n\n"

        return formatted

    def add_line_numbers(
        self, text: str, start_number: int = 1, skip_blank_lines: bool = True
    ) -> str:
        """Add line numbers to the left margin (for some court requirements)"""

        lines = text.split("\n")
        numbered_lines = []
        line_num = start_number

        for line in lines:
            if skip_blank_lines and not line.strip():
                numbered_lines.append(line)
            else:
                numbered_lines.append(f"{line_num:>3}  {line}")
                line_num += 1

        return "\n".join(numbered_lines)

    def _center_text(self, text: str) -> str:
        """Center text within the line width"""
        return text.center(self.line_width)

    def format_block_quote(
        self, quote_text: str, citation: str = None, emphasis_pattern: str = None
    ) -> str:
        """Format a block quote with proper indentation and citation"""

        # Indent the quote
        lines = quote_text.strip().split("\n")
        formatted_lines = []

        for line in lines:
            if line.strip():
                # Add emphasis if pattern provided
                if emphasis_pattern:
                    line = re.sub(
                        f"({emphasis_pattern})",
                        r"**\1**",  # Bold emphasis
                        line,
                        flags=re.IGNORECASE,
                    )
                formatted_lines.append("        " + line)
            else:
                formatted_lines.append("")

        block_quote = "\n".join(formatted_lines)

        # Add citation if provided
        if citation:
            block_quote += f"\n\n{citation}"

        return block_quote

    def format_case_citation(
        self,
        case_name: str,
        reporter: str,
        court_year: str = None,
        pinpoint: str = None,
        parenthetical: str = None,
    ) -> str:
        """Format a proper case citation"""

        citation = f"{case_name}, {reporter}"

        if pinpoint:
            citation += f", {pinpoint}"

        if court_year:
            citation += f" ({court_year})"

        if parenthetical:
            citation += f" ({parenthetical})"

        return citation

    def create_table_of_contents(self, sections: List[Dict[str, Any]]) -> str:
        """Create a table of contents for the motion"""

        toc = "TABLE OF CONTENTS\n\n"

        for section in sections:
            title = section.get("title", "")
            page = section.get("page", "")
            level = section.get("level", 1)

            # Indent sub-levels
            indent = "    " * (level - 1)

            # Create dotted line to page number
            dots_needed = 70 - len(indent) - len(title) - len(str(page))
            dots = "." * max(dots_needed, 3)

            toc += f"{indent}{title} {dots} {page}\n"

        return toc

    def create_table_of_authorities(
        self,
        cases: List[Dict[str, str]],
        statutes: List[Dict[str, str]],
        regulations: List[Dict[str, str]],
        other_authorities: List[Dict[str, str]] = None,
    ) -> str:
        """Create a table of authorities"""

        toa = "TABLE OF AUTHORITIES\n\n"

        # Cases
        if cases:
            toa += "CASES\n\n"
            for case in sorted(cases, key=lambda x: x.get("name", "")):
                name = case.get("name", "")
                pages = case.get("pages", "")
                toa += f"{name} ... {pages}\n"
            toa += "\n"

        # Statutes
        if statutes:
            toa += "STATUTES\n\n"
            for statute in sorted(statutes, key=lambda x: x.get("citation", "")):
                citation = statute.get("citation", "")
                pages = statute.get("pages", "")
                toa += f"{citation} ... {pages}\n"
            toa += "\n"

        # Regulations
        if regulations:
            toa += "REGULATIONS\n\n"
            for reg in sorted(regulations, key=lambda x: x.get("citation", "")):
                citation = reg.get("citation", "")
                pages = reg.get("pages", "")
                toa += f"{citation} ... {pages}\n"
            toa += "\n"

        # Other Authorities
        if other_authorities:
            toa += "OTHER AUTHORITIES\n\n"
            for auth in other_authorities:
                citation = auth.get("citation", "")
                pages = auth.get("pages", "")
                toa += f"{citation} ... {pages}\n"

        return toa


# Create global instance
legal_formatter = LegalFormatter()
