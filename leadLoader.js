const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const xlsx = require('xlsx');

class LeadLoader {
  /**
   * List available exported files from scraper directory (or fallback data directory)
   */
  listExportFiles(dirPath) {
    let targetPath = dirPath;
    if (targetPath && !path.isAbsolute(targetPath)) {
      targetPath = path.resolve(__dirname, targetPath);
    }
    if (!targetPath || !fs.existsSync(targetPath)) {
      const defaultExports = path.join(__dirname, 'exports');
      if (fs.existsSync(defaultExports)) {
        targetPath = defaultExports;
      } else {
        const fallback = path.join(__dirname, 'data');
        if (fs.existsSync(fallback)) {
          targetPath = fallback;
        } else {
          return [];
        }
      }
    }
    const files = fs.readdirSync(targetPath);
    return files
      .filter(f => (f.endsWith('.csv') || f.endsWith('.xlsx')) && !f.startsWith('~$'))
      .map(file => {
        const fullPath = path.join(targetPath, file);
        const stats = fs.statSync(fullPath);
        return {
          filename: file,
          fullPath,
          size: stats.size,
          lastModified: stats.mtime
        };
      })
      .sort((a, b) => b.lastModified - a.lastModified);
  }

  /**
   * Load leads from a CSV or XLSX file
   */
  async loadLeads(filePath) {
    if (!fs.existsSync(filePath)) {
      throw new Error(`File not found: ${filePath}`);
    }

    if (filePath.endsWith('.csv')) {
      return this.loadFromCSV(filePath);
    } else if (filePath.endsWith('.xlsx')) {
      return this.loadFromExcel(filePath);
    } else {
      throw new Error('Unsupported file format. Must be .csv or .xlsx');
    }
  }

  loadFromCSV(filePath) {
    return new Promise((resolve, reject) => {
      const results = [];
      fs.createReadStream(filePath)
        .pipe(csv())
        .on('data', (row) => {
          const lead = this.normalizeLeadRow(row);
          if (lead.phone) {
            results.push(lead);
          }
        })
        .on('end', () => resolve(results))
        .on('error', (err) => reject(err));
    });
  }

  loadFromExcel(filePath) {
    const workbook = xlsx.readFile(filePath);
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const rawMatrix = xlsx.utils.sheet_to_json(sheet, { header: 1 });

    if (!rawMatrix || rawMatrix.length === 0) return [];

    // Scan for header row index (matches 'name'/'dealer' and 'phone'/'mobile'/'contact')
    let headerRowIndex = 0;
    for (let i = 0; i < Math.min(rawMatrix.length, 10); i++) {
      const row = rawMatrix[i];
      if (Array.isArray(row)) {
        const rowStr = row.map(c => String(c || '').toLowerCase()).join(' ');
        if ((rowStr.includes('name') || rowStr.includes('dealer')) && (rowStr.includes('phone') || rowStr.includes('mobile') || rowStr.includes('contact'))) {
          headerRowIndex = i;
          break;
        }
      }
    }

    const headers = (rawMatrix[headerRowIndex] || []).map(h => String(h || '').trim());
    const dataRows = rawMatrix.slice(headerRowIndex + 1);

    const rows = [];
    for (const r of dataRows) {
      if (!Array.isArray(r) || r.length === 0) continue;
      const obj = {};
      headers.forEach((h, colIdx) => {
        if (h) {
          obj[h] = r[colIdx] !== undefined ? r[colIdx] : '';
        }
      });
      rows.push(obj);
    }

    return rows
      .map(row => this.normalizeLeadRow(row))
      .filter(lead => Boolean(lead.phone));
  }

  normalizeLeadRow(row) {
    // Strip BOM and normalize keys
    const cleanRow = {};
    for (const key of Object.keys(row)) {
      const normalizedKey = key.replace(/^\uFEFF/, '').trim();
      cleanRow[normalizedKey] = row[key];
    }

    // Accommodate variations in column headers
    const name = cleanRow['Dealer / Agency Name'] || cleanRow['Name'] || cleanRow['Dealer Name'] || cleanRow['Agency Name'] || '';
    const phone = cleanRow['Phone Number'] || cleanRow['Phone'] || cleanRow['Mobile'] || cleanRow['Contact'] || '';
    const website = cleanRow['Website'] || cleanRow['Web'] || cleanRow['Site'] || cleanRow['Url'] || '';
    const address = cleanRow['Full Address'] || cleanRow['Address'] || cleanRow['Location'] || '';
    const rating = cleanRow['Rating'] || '';
    const category = cleanRow['Category'] || 'Property Dealer';
    const email = cleanRow['Email Address'] || cleanRow['Email'] || '';
    const mapsLink = cleanRow['Google Maps Link'] || cleanRow['Link'] || '';

    const cleanWebsite = String(website).trim();
    const hasWebsite = Boolean(cleanWebsite && !cleanWebsite.toLowerCase().includes('google.com/maps'));

    return {
      name: String(name).trim(),
      phone: String(phone).trim(),
      website: cleanWebsite,
      hasWebsite: hasWebsite,
      address: String(address).trim(),
      rating: String(rating).trim(),
      category: String(category).trim(),
      email: String(email).trim(),
      mapsLink: String(mapsLink).trim()
    };
  }
}

module.exports = new LeadLoader();
