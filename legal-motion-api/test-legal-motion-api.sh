#!/bin/sh

# Test script for Comprehensive Legal Motion API v2.0

echo "🧪 Testing Comprehensive Legal Motion API v2.0"
echo "============================================="
echo ""

# Colors (not all terminals support these under sh, so they may be ignored)
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# API base URL
API_URL="http://localhost:8000"

# Test 1: Health Check
echo "${YELLOW}1. Health Check${NC}"
HEALTH=$(curl -s $API_URL/health 2>/dev/null)
echo "$HEALTH" | grep -q "healthy"
if [ $? -eq 0 ]; then
    echo "${GREEN}✓ Service is healthy${NC}"
else
    echo "${RED}✗ Health check failed${NC}"
    echo "Response: $HEALTH"
    exit 1
fi

# Test 2: Argument Categories
echo ""
echo "${YELLOW}2. Available Argument Categories${NC}"
CATEGORIES=$(curl -s $API_URL/api/v1/argument-categories 2>/dev/null)
echo "$CATEGORIES" | grep -q "negligence"
if [ $? -eq 0 ]; then
    echo "${GREEN}✓ Categories endpoint working${NC}"
    TOTAL_CATS=$(echo "$CATEGORIES" | grep -o '"total_categories":[0-9]*' | cut -d':' -f2)
    echo "  Total predefined categories: $TOTAL_CATS"
    echo "  Note: AI can create custom categories as needed"
else
    echo "${RED}✗ Categories endpoint failed${NC}"
fi

# Test 3: Comprehensive Motion Analysis
echo ""
echo "${YELLOW}3. Comprehensive Motion Analysis${NC}"
echo "${BLUE}Testing with motion that has multiple arguments...${NC}"

MOTION_RESPONSE=$(curl -s -X POST $API_URL/api/v1/analyze-motion \
  -H "Content-Type: application/json" \
  -d '{
    "motion_text": "DEFENDANTS MOTION IN LIMINE TO EXCLUDE EVIDENCE AND ARGUMENT AND TO STRIKE/DISMISS ACTIVE NEGLIGENCE CLAIM\n\nI. INTRODUCTION\nDefendant Performance Food Group (PFG) moves to exclude evidence and argument regarding Count II (active negligence) as it imposes no additional liability beyond Count III (vicarious liability under dangerous instrumentality doctrine).\n\nII. LEGAL STANDARD\nA. Motions in limine prevent prejudicial evidence. See Luce v. United States, 469 U.S. 38 (1984).\nB. Derivative liability requires a direct tortfeasors negligence. Grobman v. Posey, 863 So. 2d 1230, 1236 (Fla. 4th DCA 2003).\n\nIII. ARGUMENT\nA. Count II Is Duplicative and Prejudicial\n1. Both counts depend on driver Destins negligence\n2. PFG admits Destin was acting within scope of employment\n3. Dangerous instrumentality doctrine already imposes full vicarious liability. Aurbach v. Gallina, 753 So. 2d 60, 62 (Fla. 2000).\n\nB. Florida Law Prohibits Separate Negligent Hiring Claims\nWhen vicarious liability applies, negligent hiring/supervision claims should be dismissed. Clooney v. Geeting, 352 So. 2d 1216 (Fla. 2d DCA 1977).\n\nC. Allowing Both Claims Risks Improper Fault Allocation\n1. Jury cannot allocate fault between PFG and Destin separately\n2. Section 768.81 requires treating them as one entity for fault purposes\n\nIV. RELIEF REQUESTED\nPFG requests the Court:\n1. Exclude all evidence related to negligent hiring/supervision\n2. Strike Count II from the complaint\n3. Prohibit argument suggesting PFG has independent negligence",
    "case_context": "Personal injury case involving commercial vehicle accident. Plaintiff suing both driver and employer.",
    "analysis_options": {
      "extract_all_arguments": true,
      "allow_custom_categories": true
    }
  }' 2>/dev/null)

echo "$MOTION_RESPONSE" | grep -q "all_arguments"
if [ $? -eq 0 ]; then
    echo "${GREEN}✓ Comprehensive analysis completed${NC}"
    TOTAL_ARGS=$(echo "$MOTION_RESPONSE" | grep -o '"total_arguments_found":[0-9]*' | cut -d':' -f2)
    echo "  Total arguments extracted: $TOTAL_ARGS"
    echo "  Sample argument IDs:"
    echo "$MOTION_RESPONSE" | grep -o '"argument_id":"[^"]*"' | head -3 | cut -d'"' -f4 | sed 's/^/    - /'
    echo "$MOTION_RESPONSE" | grep -q "argument_groups"
    if [ $? -eq 0 ]; then
        echo "  ✓ Arguments grouped strategically"
    fi
    echo "$MOTION_RESPONSE" | grep -q "custom_categories_created"
    if [ $? -eq 0 ]; then
        echo "  ✓ Custom category support confirmed"
    fi
else
    echo "${RED}✗ Comprehensive analysis failed${NC}"
    echo "Response preview: $(echo "$MOTION_RESPONSE" | head -c 200)..."
fi

# Test 4: Multiple Arguments Same Category
echo ""
echo "${YELLOW}4. Testing Multiple Arguments in Same Category${NC}"

MULTI_ARG_RESPONSE=$(curl -s -X POST $API_URL/api/v1/analyze-motion \
  -H "Content-Type: application/json" \
  -d '{
    "motion_text": "MOTION FOR SUMMARY JUDGMENT\n\nDefendant moves for summary judgment based on multiple procedural defects:\n\n1. STATUTE OF LIMITATIONS: This action is time-barred under the two-year statute. Filed 2/15/2024 for incident on 2/1/2022.\n\n2. LACK OF PERSONAL JURISDICTION: Defendant has no contacts with Florida. No business, property, or transactions here.\n\n3. IMPROPER VENUE: Even if jurisdiction exists, venue is improper under 28 U.S.C. § 1391. No events occurred in this district.\n\n4. FAILURE TO JOIN NECESSARY PARTY: The actual property owner must be joined under Rule 19. Their absence prevents complete relief.\n\n5. PRIOR PENDING ACTION: This identical claim is already pending in Georgia state court (Case No. 2023-CV-1234).",
    "case_context": "Federal diversity case"
  }' 2>/dev/null)

echo "$MULTI_ARG_RESPONSE" | grep -q "all_arguments"
if [ $? -eq 0 ]; then
    TOTAL_PROCEDURAL=$(echo "$MULTI_ARG_RESPONSE" | grep -o '"category":"procedural_[^"]*"' | wc -l)
    echo "${GREEN}✓ Multiple procedural arguments detected: ~$TOTAL_PROCEDURAL${NC}"
else
    echo "${RED}✗ Failed to extract multiple similar arguments${NC}"
fi

# Test 5: Analysis Statistics
echo ""
echo "${YELLOW}5. API Capabilities Check${NC}"
STATS=$(curl -s $API_URL/api/v1/analysis-stats 2>/dev/null)
echo "$STATS" | grep -q "capabilities"
if [ $? -eq 0 ]; then
    echo "${GREEN}✓ API statistics available${NC}"
else
    echo "${YELLOW}! Statistics endpoint not available${NC}"
fi

# Final Summary
echo ""
echo "${GREEN}=====================================
        ANALYSIS SUMMARY
=====================================${NC}"

echo "$MOTION_RESPONSE" | grep -q "all_arguments"
if [ $? -eq 0 ]; then
    echo "${GREEN}✅ Comprehensive Motion Analyzer v2.0 is working!${NC}"
else
    echo "${RED}❌ There are issues with the comprehensive analyzer${NC}"
fi
