---
name: travel-planner
category: planning
description: >
  Use this skill when the user asks to create a travel plan, itinerary, weekend trip plan, 
  vacation schedule, or travel guide. Triggers on: "plan a trip", "create travel plan", 
  "weekend itinerary", "travel to", "visit", "trip planning", "travel guide".
---

# Travel Planner

## When to use
Use when users want to plan trips, create itineraries, or get travel recommendations for specific destinations.

## Procedure

1. Gather trip details from user or infer reasonable defaults:
   - Destination
   - Duration (weekend, week, etc.)
   - Travel dates or season
   - Interests/preferences (nature, culture, food, adventure, etc.)
   - Budget level (budget, mid-range, luxury)
   - Group size and composition
   - Transportation method (car, plane, train, etc.)

2. Research and compile travel information:
   - Transportation options to/from destination
   - Accommodation recommendations with parking details
   - Top attractions and activities
   - Local dining recommendations
   - Weather considerations
   - Practical tips (what to pack, local customs, etc.)

3. For accommodation recommendations, always include:
   - Hotel/lodging options by budget category
   - **Car parking availability and details:**
     - Free vs paid parking options
     - On-site parking vs nearby alternatives
     - Valet services if available
     - Parking restrictions or time limits
     - Security features (covered, gated, surveillance)
     - Electric vehicle charging stations if available
     - Alternative parking solutions (street parking, public lots, park-and-ride)
   - Proximity to attractions and transportation
   - Amenities and special features

4. Create a structured itinerary with:
   - Day-by-day schedule
   - Time estimates for activities
   - Transportation between locations (including parking considerations)
   - Meal suggestions
   - Alternative options for different weather
   - Parking recommendations for each destination/activity

5. Format as a comprehensive travel document including:
   - Trip overview
   - Detailed daily itinerary
   - Accommodation guide with parking details
   - Transportation and parking information
   - Dining recommendations
   - Packing checklist
   - Emergency contacts and practical info

6. Save the travel plan as a formatted document to outputs/

## Rules
- Always include practical details like travel times and costs where possible
- **Always mention parking details when recommending accommodations**
- Include parking costs in budget considerations
- Provide alternatives for weather-dependent activities
- Consider the physical demands of activities
- Include both popular attractions and hidden gems
- Suggest realistic time allocations for activities
- For car travelers, include parking tips for major attractions

## Output
Create a comprehensive travel plan document saved to outputs/ as either:
- A formatted text file (.txt) for basic itineraries
- A Word document (.docx) for more detailed, professional plans using the docx skill
- Include maps, contact details, parking information, and booking links where helpful