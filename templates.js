/**
 * WhatsApp Outreach Templates Engine
 * Powered by Structured Niches Configuration (Tier 1, Tier 2, Tier 3)
 * Provides ultra-short, natural, conversational pitches tailored to each business,
 * and smart follow-up message generators (1st & 2nd follow-up).
 */

const fs = require('fs');
const path = require('path');

// Load Niches Configuration
let nichesConfig = null;
try {
  const raw = fs.readFileSync(path.join(__dirname, 'niches_config.json'), 'utf8');
  nichesConfig = JSON.parse(raw);
} catch (e) {
  console.warn('Could not load niches_config.json, using fallback templates');
}

/**
 * Clean dealer/business name by stripping promotional suffixes like ': Property dealer in ...'
 */
function cleanDealerName(rawName) {
  if (!rawName) return 'Sir/Madam';
  let name = String(rawName).trim();
  // Strip common promo suffixes like " : ...", " | ...", " - ..."
  name = name.split(':')[0].split('|')[0].split(' - ')[0].trim();
  // Remove leading/trailing non-alphanumeric except spaces and periods (to keep Dr.)
  name = name.replace(/^[^a-zA-Z0-9.\s]+|[^a-zA-Z0-9.\s]+$/g, '').trim();
  return name || String(rawName).trim();
}

/**
 * Clean address to extract just the locality and city
 */
function cleanDealerAddress(rawAddress) {
  if (!rawAddress) return 'your area';
  const parts = String(rawAddress)
    .split(',')
    .map(p => p.trim())
    .filter(Boolean);

  if (parts.length === 0) return 'your area';

  // Filter out standalone pincodes (6 digits)
  const cleanParts = parts
    .map(p => p.replace(/\b\d{6}\b/g, '').trim())
    .filter(Boolean);

  if (cleanParts.length >= 2) {
    return cleanParts.slice(-2).join(', ');
  }
  return cleanParts[0] || parts[0] || 'your area';
}

/**
 * Find matching niche configuration based on lead category, name, or search query
 */
function findMatchingNiche(lead) {
  if (!nichesConfig) return null;

  const textToSearch = [
    lead.category || '',
    lead.niche || '',
    lead.searchQuery || '',
    lead.name || ''
  ].join(' ').toLowerCase();

  const allTiers = ['tier_1', 'tier_2', 'tier_3'];
  for (const tierKey of allTiers) {
    const tier = nichesConfig[tierKey];
    if (!tier || !tier.niches) continue;

    for (const niche of tier.niches) {
      for (const kw of niche.keywords) {
        if (textToSearch.includes(kw.toLowerCase())) {
          return { ...niche, tierKey };
        }
      }
    }
  }

  // Default to tier 1 real estate
  return nichesConfig.tier_1?.niches[0] || null;
}

/**
 * Fallback baseline templates (Real estate & universal)
 */
const fallbackTemplates = [
  // Variation 1: Hinglish Natural
  `Namaste {name} ji,

Main {address} me aapka profile dekh raha tha.
Aapke paas available properties dekhne ke liye koi website link hai, ya fir aap inventory direct WhatsApp par hi share karte hain?

Actually humne property consultants ke liye ek simple 1-click WhatsApp showcase demo banaya hai. Agar aap kahen to 1 minute ka preview link share karun?

- {senderName}`,

  // Variation 2: Casual English
  `Hi {name},

Came across your real estate business in {address}.

Quick question — do you have a website link to view your active properties, or do you share listings directly on WhatsApp?

I recently designed a simple mobile portfolio demo tailored for property consultants (with direct WhatsApp inquiry buttons). 

Would you be open to checking out a quick 1-minute demo link?

Best,
{senderName}`
];

/**
 * Returns a personalized, non-salesy outreach message tailored to the specific niche.
 * @param {object} lead 
 * @param {number} [templateIndex]
 * @param {string} [senderName]
 * @returns {string}
 */
function getPersonalizedMessage(lead, templateIndex, senderName = 'Deepaktusir') {
  const matched = findMatchingNiche(lead);

  let rawTemplate = '';
  if (matched) {
    // Choose between Hinglish and English based on templateIndex
    const useHinglish = typeof templateIndex === 'number' ? (templateIndex % 2 === 0) : true;
    rawTemplate = useHinglish ? (matched.pitch_hinglish || matched.pitch_english) : (matched.pitch_english || matched.pitch_hinglish);
  } else {
    const idx = typeof templateIndex === 'number' ? templateIndex % fallbackTemplates.length : 0;
    rawTemplate = fallbackTemplates[idx];
  }

  const cleanName = cleanDealerName(lead.name);
  const cleanAddress = cleanDealerAddress(lead.address);

  let text = rawTemplate;
  text = text.replace(/{name}/g, cleanName);
  text = text.replace(/{address}/g, cleanAddress);
  text = text.replace(/{category}/g, lead.category || matched?.name || 'Business');
  text = text.replace(/{senderName}/g, senderName);

  return text;
}

/**
 * Returns a personalized follow-up message based on whether it is 1st or 2nd follow-up,
 * and whether the recipient has seen (blue ticked) the previous message or not.
 * @param {object} lead
 * @param {number} followUpNumber (1 or 2)
 * @param {boolean} isSeen
 * @param {string} senderName
 * @returns {string}
 */
function getFollowUpMessage(lead, followUpNumber = 1, isSeen = false, senderName = 'Deepaktusir') {
  const cleanName = cleanDealerName(lead.name);
  const cleanAddress = cleanDealerAddress(lead.address);

  let text = '';
  if (followUpNumber === 1) {
    if (isSeen) {
      // Blue Ticked / Read, but no reply
      text = `Namaste {name} ji, just checking agar aapko mera previous message mila tha? Koi jaldi nahi hai, agar aap kahen to bas 1 minute ka demo link yahan share kar dun?\n\n- {senderName}`;
    } else {
      // Unopened / Grey Tick - Gentle bump
      text = `Hi {name} ji, hope you are doing well! Ek quick question tha regarding your business in {address} — kya aap properties/work catalog direct WhatsApp par hi share karte hain?\n\n- {senderName}`;
    }
  } else {
    // Follow-up 2: The Respectful Breakup Message (Final attempt before moving to Dead List)
    text = `Namaste {name} ji, last message meri taraf se taaki aapka time waste na ho. Agar aapko apne business ke liye custom showcase demo nahi dekhna to no problem at all! Wishing you great business ahead.\n\n- {senderName}`;
  }

  text = text.replace(/{name}/g, cleanName);
  text = text.replace(/{address}/g, cleanAddress);
  text = text.replace(/{category}/g, lead.category || 'Business');
  text = text.replace(/{senderName}/g, senderName);

  return text;
}

module.exports = {
  nichesConfig,
  cleanDealerName,
  cleanDealerAddress,
  findMatchingNiche,
  getPersonalizedMessage,
  getFollowUpMessage,
  templates: fallbackTemplates
};
