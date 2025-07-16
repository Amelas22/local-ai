#!/usr/bin/env python3
"""
Standalone script to initialize shared knowledge databases
Run this directly: python init_shared_knowledge.py
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import logging
from datetime import datetime

# Now import after path is set
from src.data_loaders.florida_statutes_loader import FloridaStatutesLoader
from src.data_loaders.fmcsr_loader import FMCSRLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def initialize_florida_statutes():
    """Load common Florida statutes into shared database"""
    logger.info("Initializing Florida statutes...")

    loader = FloridaStatutesLoader()

    # Load common statutes for personal injury and commercial vehicle cases
    statutes = [
        {
            "number": "768.81",
            "title": "Comparative fault",
            "content": """(1) DEFINITIONS.—As used in this section:
(a) "Economic damages" means damages for objectively verifiable monetary losses including, but not limited to:
1. Past lost income and future lost income reduced to present value.
2. Medical and funeral expenses.
3. Lost support and services.
4. Replacement value of lost personal property.
5. Loss of appraised fair market value of real property.
6. Costs of construction repairs, including labor, overhead, and profit.
7. Any other economic loss that would not have occurred but for the injury giving rise to the cause of action.

(b) "Noneconomic damages" means damages for:
1. Pain and suffering.
2. Inconvenience.
3. Mental anguish.
4. Loss of capacity for enjoyment of life.

(2) EFFECT OF CONTRIBUTORY FAULT.—In a negligence action, contributory fault chargeable to the claimant diminishes proportionately the amount awarded as economic and noneconomic damages for an injury attributable to the claimant's contributory fault, but does not bar recovery.

(3) APPORTIONMENT OF DAMAGES.—In cases to which this section applies, the court shall enter judgment against each party liable on the basis of such party's percentage of fault.""",
        },
        {
            "number": "316.193",
            "title": "Driving under the influence",
            "content": """(1) A person is guilty of the offense of driving under the influence and is subject to punishment as provided in subsection (2) if the person is driving or in actual physical control of a vehicle within this state and:
(a) The person is under the influence of alcoholic beverages, any chemical substance set forth in s. 877.111, or any substance controlled under chapter 893, when affected to the extent that the person's normal faculties are impaired;
(b) The person has a blood-alcohol level of 0.08 or more grams of alcohol per 100 milliliters of blood; or
(c) The person has a breath-alcohol level of 0.08 or more grams of alcohol per 210 liters of breath.""",
        },
        {
            "number": "768.125",
            "title": "Admissibility of evidence relating to seat belts",
            "content": """In any action for personal injuries or wrongful death arising out of the ownership, maintenance, operation, or control of a motor vehicle, evidence of the failure of the plaintiff to wear an available and operational seat belt in violation of s. 316.614 is admissible to the extent provided in this section.

(1) Such evidence may be considered by the trier of fact in determining comparative fault.
(2) If the defendant pleads that the plaintiff failed to wear an available and operational seat belt, the defendant has the burden of proving:
(a) The plaintiff failed to wear an available and operational seat belt;
(b) The plaintiff's failure to wear a seat belt was unreasonable under the circumstances; and
(c) The plaintiff's failure to wear a seat belt contributed to the plaintiff's injuries.""",
        },
        {
            "number": "627.737",
            "title": "Tort exemption; limitation on right to damages; punitive damages",
            "content": """(1) Every owner, registrant, operator, or occupant of a motor vehicle with respect to which security has been provided as required by ss. 627.730-627.7405, and every person or organization legally responsible for her or his acts or omissions, is hereby exempted from tort liability for damages because of bodily injury, sickness, or disease arising out of the ownership, maintenance, or use of such motor vehicle in this state.""",
        },
        {
            "number": "768.72",
            "title": "Pleading in civil actions; claim for punitive damages",
            "content": """(1) In any civil action, no claim for punitive damages shall be permitted unless there is a reasonable showing by evidence in the record or proffered by the claimant which would provide a reasonable basis for recovery of such damages.

(2) A defendant may be held liable for punitive damages only if the trier of fact, based on clear and convincing evidence, finds that the defendant was personally guilty of intentional misconduct or gross negligence.""",
        },
    ]

    # Load each statute
    for statute in statutes:
        await loader.load_statute(
            statute_number=statute["number"],
            title=statute["title"],
            content=statute["content"],
            chapter="Chapter 768 - Negligence"
            if statute["number"].startswith("768")
            else "Chapter 316 - Traffic"
            if statute["number"].startswith("316")
            else "Chapter 627 - Insurance",
            effective_date=datetime(2024, 1, 1),
        )

    logger.info("Florida statutes initialized successfully")


async def initialize_fmcsr():
    """Load common FMCSR regulations into shared database"""
    logger.info("Initializing FMCSR regulations...")

    loader = FMCSRLoader()

    # Load critical FMCSR parts for commercial vehicle cases
    regulations = [
        {
            "part": "395",
            "section": "8",
            "title": "Driver's record of duty status",
            "content": """(a) Except for a private motor carrier of passengers (nonbusiness), every motor carrier shall require every driver to record his/her duty status for each 24-hour period using the method prescribed in paragraphs (a)(1) through (5) of this section.

(1) Every driver who operates a commercial motor vehicle shall record his/her duty status, in duplicate, for each 24-hour period.

(2) The duty status time shall be recorded on a specified grid or an electronic logging device (ELD) that complies with subpart B of this part.

(3) The duty status shall be recorded as follows:
(i) "Off duty" or "OFF"
(ii) "Sleeper berth" or "SB"
(iii) "Driving" or "D"
(iv) "On-duty not driving" or "ON"

(e) Failure to complete the record of duty activities, failure to preserve a record of such duty activities, or making of false reports in connection with such duty activities shall make the driver and/or the carrier liable to prosecution.""",
        },
        {
            "part": "392",
            "section": "3",
            "title": "Ill or fatigued operator",
            "content": """No driver shall operate a commercial motor vehicle, and a motor carrier shall not require or permit a driver to operate a commercial motor vehicle, while the driver's ability or alertness is so impaired, or so likely to become impaired, through fatigue, illness, or any other cause, as to make it unsafe for him/her to begin or continue to operate the commercial motor vehicle.

GUIDANCE: A driver who informs a motor carrier that he or she needs immediate rest shall be permitted at least 10 consecutive hours off-duty before the driver is again required to operate a commercial motor vehicle.""",
        },
        {
            "part": "396",
            "section": "3",
            "title": "Inspection, repair, and maintenance",
            "content": """(a) General. Every motor carrier and intermodal equipment provider must systematically inspect, repair, and maintain, or cause to be systematically inspected, repaired, and maintained, all motor vehicles and intermodal equipment subject to its control.

(b) Required records. Motor carriers, except for a private motor carrier of passengers (nonbusiness), must maintain, or cause to be maintained, records for each motor vehicle they control for 30 consecutive days. Intermodal equipment providers must maintain or cause to be maintained, records for each unit of intermodal equipment they tender or intend to tender to a motor carrier.""",
        },
        {
            "part": "391",
            "section": "11",
            "title": "General qualifications of drivers",
            "content": """(a) A person shall not drive a commercial motor vehicle unless he/she is qualified to drive a commercial motor vehicle. Except as provided in § 391.63, a motor carrier shall not require or permit a person to drive a commercial motor vehicle unless that person is qualified to drive a commercial motor vehicle.

(b) Except as provided in subpart G of this part, a person is qualified to drive a motor vehicle if he/she:
(1) Is at least 21 years old;
(2) Can read and speak the English language sufficiently to converse with the general public, to understand highway traffic signs and signals in the English language, to respond to official inquiries, and to make entries on reports and records;
(3) Can, by reason of experience, training, or both, safely operate the type of commercial motor vehicle he/she drives;
(4) Is physically qualified to drive a commercial motor vehicle in accordance with subpart E of this part;
(5) Has a currently valid commercial motor vehicle operator's license issued only by one State or jurisdiction;
(6) Has prepared and furnished the motor carrier that employs him/her with the list of violations or the certificate required by § 391.27;
(7) Is not disqualified to drive a commercial motor vehicle under the rules in § 391.15.""",
        },
        {
            "part": "382",
            "section": "301",
            "title": "Pre-employment testing",
            "content": """(a) Prior to the first time a driver performs safety-sensitive functions for an employer, the driver shall undergo testing for controlled substances as a condition prior to being used, unless the employer uses the exception in paragraph (b) of this section. No employer shall allow a driver, who the employer intends to hire or use, to perform safety-sensitive functions unless the employer has received a controlled substances test result from the MRO or C/TPA indicating a verified negative test result for that driver.

(b) An employer is not required to administer a controlled substances test required by paragraph (a) of this section if:
(1) The driver has participated in a controlled substances testing program that meets the requirements of this part within the previous 30 days; and
(2) While participating in that program, either:
(i) Was tested for controlled substances within the past 6 months (from the date of application with the employer), or
(ii) Participated in the random controlled substances testing program for the previous 12 months (from the date of application with the employer).""",
        },
    ]

    # Load each regulation
    for reg in regulations:
        await loader.load_regulation(
            part=reg["part"],
            section=reg["section"],
            title=reg["title"],
            content=reg["content"],
            effective_date=datetime(2024, 1, 1),
        )

    logger.info("FMCSR regulations initialized successfully")


async def main():
    """Initialize all shared knowledge databases"""
    logger.info("Starting shared knowledge database initialization...")

    try:
        # Initialize Florida statutes
        await initialize_florida_statutes()

        # Initialize FMCSR
        await initialize_fmcsr()

        logger.info("All shared knowledge databases initialized successfully!")

    except Exception as e:
        logger.error(f"Error initializing shared knowledge: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
