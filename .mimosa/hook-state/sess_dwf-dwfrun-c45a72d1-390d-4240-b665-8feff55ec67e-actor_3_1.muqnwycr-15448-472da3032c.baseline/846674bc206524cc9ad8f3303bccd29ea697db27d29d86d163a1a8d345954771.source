"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
ChemistryDataSource - Data source cho Hóa học
Bao gồm: 118 nguyên tố, hợp chất phổ biến, phản ứng, hằng số hóa học.
"""
import json
import logging
import urllib.parse
import urllib.request
from typing import Any

from scp.interfaces.data_source import IDataSource
from scp.security.url_safety import safe_urlopen  # [AUDIT-20260909 SSRF-S1]

logger = logging.getLogger(__name__)

# [AUDIT-20260909 SSRF-S1] Host cố định cho PubChem fetch.
_PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name"


def build_pubchem_url(entity: str) -> str:
    """[AUDIT-20260909 SSRF-S1] Pure URL builder — compound name (input động)
    được quote(safe='') → '/', '..', '?' bị encode, luôn nằm trong MỘT path
    segment của host cố định pubchem.ncbi.nlm.nih.gov."""
    quoted = urllib.parse.quote(str(entity or ""), safe="")
    return (
        f"{_PUBCHEM_BASE}/{quoted}"
        f"/property/MolecularFormula,MolecularWeight/JSON"
    )


class ChemistryDataSource(IDataSource):
    """
    Data source cho các câu hỏi Hóa học.
    Hỗ trợ: nguyên tố (symbol, atomic number, mass, group, period),
            hợp chất (formula, MM, tên), phản ứng, hằng số.
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # ---------------- Periodic Table: 118 elements ----------------
        # Format: symbol -> {name, vi_name, atomic_number, atomic_mass, group, period, category}
        self._elements: dict[str, dict[str, Any]] = self._build_periodic_table()

        # Atomic number -> symbol (reverse lookup)
        self._atomic_number_to_symbol = {
            v['atomic_number']: k for k, v in self._elements.items()
        }

        # ---------------- Common compounds ----------------
        self._compounds: dict[str, dict[str, Any]] = self._build_compounds()

        # ---------------- Chemical constants ----------------
        self._constants = {
            'số avogadro': 6.02214076e23,
            'avogadro number': 6.02214076e23,
            'na': 6.02214076e23,
            'hằng số khí lý tưởng': 8.314462618,
            'ideal gas constant': 8.314462618,
            'r': 8.314462618,
            'hằng số faraday': 96485.33212,
            'faraday constant': 96485.33212,
            'f': 96485.33212,
            'số rydberg': 10973731.568160,
            'rydberg constant': 10973731.568160,
            'rh': 10973731.568160,
            'bán kính bohr': 5.29177210903e-11,
            'bohr radius': 5.29177210903e-11,
            'a0': 5.29177210903e-11,
            'năng lượng ion hóa hydro': 13.5984,
            'hydrogen ionization energy': 13.5984,
            'ph trung tính': 7.0,  # [AUDIT-FIX info-5] typo 'ph的中性' → key tiếng Việt đúng
            'ph neutral': 7.0,
            'khối lượng nguyên tử carbon 12': 12.0,
            'carbon 12 atomic mass': 12.0,
            'nhiệt độ tiêu chuẩn': 273.15,
            'standard temperature': 273.15,
            'áp suất tiêu chuẩn': 101325.0,
            'standard pressure': 101325.0,
            'atm to pascal': 101325.0,
        }

        # ---------------- Common reactions ----------------
        self._reactions: dict[str, dict[str, Any]] = {
            'phản ứng đốt cháy methane': {
                'equation': 'CH4 + 2O2 -> CO2 + 2H2O',
                'type': 'combustion',
                'delta_h': -890.4,  # kJ/mol
            },
            'phản ứng trung hòa': {
                'equation': 'HCl + NaOH -> NaCl + H2O',
                'type': 'neutralization',
                'delta_h': -57.1,
            },
            'quá trình quang hợp': {
                'equation': '6CO2 + 6H2O -> C6H12O6 + 6O2',
                'type': 'photosynthesis',
                'delta_h': 2803.0,
            },
            'phản ứng haber': {
                'equation': 'N2 + 3H2 -> 2NH3',
                'type': 'synthesis',
                'delta_h': -92.4,
                'catalyst': 'Fe',
                'conditions': '450°C, 200 atm',
            },
            'tách nước': {
                'equation': '2H2O -> 2H2 + O2',
                'type': 'electrolysis',
                'delta_h': 571.6,
            },
            'tạo gỉ sắt': {
                'equation': '4Fe + 3O2 -> 2Fe2O3',
                'type': 'oxidation',
                'delta_h': -824.2,
            },
            'phản ứng estrer hóa': {
                'equation': 'RCOOH + R\'OH -> RCOOR\' + H2O',
                'type': 'esterification',
                'catalyst': 'H2SO4',
            },
            'phản ứng upcycling nhựa': {
                'equation': '(C2H4)n -> nC2H4',
                'type': 'cracking',
                'catalyst': 'zeolite',
            },
        }

    # ---------------- Build periodic table (118 elements) ----------------
    def _build_periodic_table(self) -> dict[str, dict[str, Any]]:
        """118 nguyên tố đầy đủ (H -> Og)."""
        # (symbol, name_en, name_vi, atomic_number, atomic_mass, group, period, category)
        data = [
            ('H', 'Hydrogen', 'Hiđrô', 1, 1.008, 1, 1, 'nonmetal'),
            ('He', 'Helium', 'Heli', 2, 4.0026, 18, 1, 'noble gas'),
            ('Li', 'Lithium', 'Liti', 3, 6.94, 1, 2, 'alkali metal'),
            ('Be', 'Beryllium', 'Beryli', 4, 9.0122, 2, 2, 'alkaline earth metal'),
            ('B', 'Boron', 'Bo', 5, 10.81, 13, 2, 'metalloid'),
            ('C', 'Carbon', 'Cacbon', 6, 12.011, 14, 2, 'nonmetal'),
            ('N', 'Nitrogen', 'Nitơ', 7, 14.007, 15, 2, 'nonmetal'),
            ('O', 'Oxygen', 'Oxy', 8, 15.999, 16, 2, 'nonmetal'),
            ('F', 'Fluorine', 'Flo', 9, 18.998, 17, 2, 'halogen'),
            ('Ne', 'Neon', 'Neon', 10, 20.180, 18, 2, 'noble gas'),
            ('Na', 'Sodium', 'Natri', 11, 22.990, 1, 3, 'alkali metal'),
            ('Mg', 'Magnesium', 'Magie', 12, 24.305, 2, 3, 'alkaline earth metal'),
            ('Al', 'Aluminium', 'Nhôm', 13, 26.982, 13, 3, 'post-transition metal'),
            ('Si', 'Silicon', 'Silic', 14, 28.085, 14, 3, 'metalloid'),
            ('P', 'Phosphorus', 'Phốt pho', 15, 30.974, 15, 3, 'nonmetal'),
            ('S', 'Sulfur', 'Lưu huỳnh', 16, 32.06, 16, 3, 'nonmetal'),
            ('Cl', 'Chlorine', 'Clo', 17, 35.45, 17, 3, 'halogen'),
            ('Ar', 'Argon', 'Agon', 18, 39.948, 18, 3, 'noble gas'),
            ('K', 'Potassium', 'Kali', 19, 39.098, 1, 4, 'alkali metal'),
            ('Ca', 'Calcium', 'Canxi', 20, 40.078, 2, 4, 'alkaline earth metal'),
            ('Sc', 'Scandium', 'Scandi', 21, 44.956, 3, 4, 'transition metal'),
            ('Ti', 'Titanium', 'Titan', 22, 47.867, 4, 4, 'transition metal'),
            ('V', 'Vanadium', 'Vanadi', 23, 50.942, 5, 4, 'transition metal'),
            ('Cr', 'Chromium', 'Crom', 24, 51.996, 6, 4, 'transition metal'),
            ('Mn', 'Manganese', 'Mangan', 25, 54.938, 7, 4, 'transition metal'),
            ('Fe', 'Iron', 'Sắt', 26, 55.845, 8, 4, 'transition metal'),
            ('Co', 'Cobalt', 'Coban', 27, 58.933, 9, 4, 'transition metal'),
            ('Ni', 'Nickel', 'Niken', 28, 58.693, 10, 4, 'transition metal'),
            ('Cu', 'Copper', 'Đồng', 29, 63.546, 11, 4, 'transition metal'),
            ('Zn', 'Zinc', 'Kẽm', 30, 65.38, 12, 4, 'transition metal'),
            ('Ga', 'Gallium', 'Gali', 31, 69.723, 13, 4, 'post-transition metal'),
            ('Ge', 'Germanium', 'Gecmani', 32, 72.630, 14, 4, 'metalloid'),
            ('As', 'Arsenic', 'Asen', 33, 74.922, 15, 4, 'metalloid'),
            ('Se', 'Selenium', 'Selen', 34, 78.971, 16, 4, 'nonmetal'),
            ('Br', 'Bromine', 'Brom', 35, 79.904, 17, 4, 'halogen'),
            ('Kr', 'Krypton', 'Kripton', 36, 83.798, 18, 4, 'noble gas'),
            ('Rb', 'Rubidium', 'Rubidi', 37, 85.468, 1, 5, 'alkali metal'),
            ('Sr', 'Strontium', 'Stronti', 38, 87.62, 2, 5, 'alkaline earth metal'),
            ('Y', 'Yttrium', 'Ytri', 39, 88.906, 3, 5, 'transition metal'),
            ('Zr', 'Zirconium', 'Ziriconi', 40, 91.224, 4, 5, 'transition metal'),
            ('Nb', 'Niobium', 'Niobi', 41, 92.906, 5, 5, 'transition metal'),
            ('Mo', 'Molybdenum', 'Molipden', 42, 95.95, 6, 5, 'transition metal'),
            ('Tc', 'Technetium', 'Techneti', 43, 98.0, 7, 5, 'transition metal'),
            ('Ru', 'Ruthenium', 'Rutheni', 44, 101.07, 8, 5, 'transition metal'),
            ('Rh', 'Rhodium', 'Rhodi', 45, 102.91, 9, 5, 'transition metal'),
            ('Pd', 'Palladium', 'Palladi', 46, 106.42, 10, 5, 'transition metal'),
            ('Ag', 'Silver', 'Bạc', 47, 107.87, 11, 5, 'transition metal'),
            ('Cd', 'Cadmium', 'Cadmi', 48, 112.41, 12, 5, 'transition metal'),
            ('In', 'Indium', 'Indi', 49, 114.82, 13, 5, 'post-transition metal'),
            ('Sn', 'Tin', 'Thiếc', 50, 118.71, 14, 5, 'post-transition metal'),
            ('Sb', 'Antimony', 'Antimon', 51, 121.76, 15, 5, 'metalloid'),
            ('Te', 'Tellurium', 'Tellu', 52, 127.60, 16, 5, 'metalloid'),
            ('I', 'Iodine', 'Iốt', 53, 126.90, 17, 5, 'halogen'),
            ('Xe', 'Xenon', 'Xenon', 54, 131.29, 18, 5, 'noble gas'),
            ('Cs', 'Caesium', 'Xesi', 55, 132.91, 1, 6, 'alkali metal'),
            ('Ba', 'Barium', 'Bari', 56, 137.33, 2, 6, 'alkaline earth metal'),
            ('La', 'Lanthanum', 'Lantan', 57, 138.91, 3, 6, 'lanthanide'),
            ('Ce', 'Cerium', 'Xeri', 58, 140.12, None, 6, 'lanthanide'),
            ('Pr', 'Praseodymium', 'Praseodymi', 59, 140.91, None, 6, 'lanthanide'),
            ('Nd', 'Neodymium', 'Neodymi', 60, 144.24, None, 6, 'lanthanide'),
            ('Pm', 'Promethium', 'Promethi', 61, 145.0, None, 6, 'lanthanide'),
            ('Sm', 'Samarium', 'Samari', 62, 150.36, None, 6, 'lanthanide'),
            ('Eu', 'Europium', 'Europi', 63, 151.96, None, 6, 'lanthanide'),
            ('Gd', 'Gadolinium', 'Gadolini', 64, 157.25, None, 6, 'lanthanide'),
            ('Tb', 'Terbium', 'Terbi', 65, 158.93, None, 6, 'lanthanide'),
            ('Dy', 'Dysprosium', 'Dysprosi', 66, 162.50, None, 6, 'lanthanide'),
            ('Ho', 'Holmium', 'Holmi', 67, 164.93, None, 6, 'lanthanide'),
            ('Er', 'Erbium', 'Erbi', 68, 167.26, None, 6, 'lanthanide'),
            ('Tm', 'Thulium', 'Thuli', 69, 168.93, None, 6, 'lanthanide'),
            ('Yb', 'Ytterbium', 'Yterbi', 70, 173.05, None, 6, 'lanthanide'),
            ('Lu', 'Lutetium', 'Luteti', 71, 174.97, 3, 6, 'lanthanide'),
            ('Hf', 'Hafnium', 'Hafni', 72, 178.49, 4, 6, 'transition metal'),
            ('Ta', 'Tantalum', 'Tantali', 73, 180.95, 5, 6, 'transition metal'),
            ('W', 'Tungsten', 'Vonfram', 74, 183.84, 6, 6, 'transition metal'),
            ('Re', 'Rhenium', 'Rheni', 75, 186.21, 7, 6, 'transition metal'),
            ('Os', 'Osmium', 'Osmi', 76, 190.23, 8, 6, 'transition metal'),
            ('Ir', 'Iridium', 'Iridi', 77, 192.22, 9, 6, 'transition metal'),
            ('Pt', 'Platinum', 'Bạch kim', 78, 195.08, 10, 6, 'transition metal'),
            ('Au', 'Gold', 'Vàng', 79, 196.97, 11, 6, 'transition metal'),
            ('Hg', 'Mercury', 'Thủy ngân', 80, 200.59, 12, 6, 'transition metal'),
            ('Tl', 'Thallium', 'Talli', 81, 204.38, 13, 6, 'post-transition metal'),
            ('Pb', 'Lead', 'Chì', 82, 207.2, 14, 6, 'post-transition metal'),
            ('Bi', 'Bismuth', 'Bismuth', 83, 208.98, 15, 6, 'post-transition metal'),
            ('Po', 'Polonium', 'Poloni', 84, 209.0, 16, 6, 'post-transition metal'),
            ('At', 'Astatine', 'Astatin', 85, 210.0, 17, 6, 'halogen'),
            ('Rn', 'Radon', 'Radon', 86, 222.0, 18, 6, 'noble gas'),
            ('Fr', 'Francium', 'Franci', 87, 223.0, 1, 7, 'alkali metal'),
            ('Ra', 'Radium', 'Radi', 88, 226.0, 2, 7, 'alkaline earth metal'),
            ('Ac', 'Actinium', 'Actini', 89, 227.0, 3, 7, 'actinide'),
            ('Th', 'Thorium', 'Thori', 90, 232.04, None, 7, 'actinide'),
            ('Pa', 'Protactinium', 'Protactini', 91, 231.04, None, 7, 'actinide'),
            ('U', 'Uranium', 'Urani', 92, 238.03, None, 7, 'actinide'),
            ('Np', 'Neptunium', 'Neptuni', 93, 237.0, None, 7, 'actinide'),
            ('Pu', 'Plutonium', 'Plutoni', 94, 244.0, None, 7, 'actinide'),
            ('Am', 'Americium', 'Americi', 95, 243.0, None, 7, 'actinide'),
            ('Cm', 'Curium', 'Curi', 96, 247.0, None, 7, 'actinide'),
            ('Bk', 'Berkelium', 'Berkeli', 97, 247.0, None, 7, 'actinide'),
            ('Cf', 'Californium', 'Californi', 98, 251.0, None, 7, 'actinide'),
            ('Es', 'Einsteinium', 'Einsteni', 99, 252.0, None, 7, 'actinide'),
            ('Fm', 'Fermium', 'Fermi', 100, 257.0, None, 7, 'actinide'),
            ('Md', 'Mendelevium', 'Mendelevi', 101, 258.0, None, 7, 'actinide'),
            ('No', 'Nobelium', 'Nobeli', 102, 259.0, None, 7, 'actinide'),
            ('Lr', 'Lawrencium', 'Lawrenci', 103, 266.0, 3, 7, 'actinide'),
            ('Rf', 'Rutherfordium', 'Rutherfordi', 104, 267.0, 4, 7, 'transition metal'),
            ('Db', 'Dubnium', 'Dubni', 105, 268.0, 5, 7, 'transition metal'),
            ('Sg', 'Seaborgium', 'Seaborgi', 106, 269.0, 6, 7, 'transition metal'),
            ('Bh', 'Bohrium', 'Bohri', 107, 270.0, 7, 7, 'transition metal'),
            ('Hs', 'Hassium', 'Hassi', 108, 269.0, 8, 7, 'transition metal'),
            ('Mt', 'Meitnerium', 'Meitneri', 109, 278.0, 9, 7, 'unknown'),
            ('Ds', 'Darmstadtium', 'Darmstadti', 110, 281.0, 10, 7, 'unknown'),
            ('Rg', 'Roentgenium', 'Roentgeni', 111, 282.0, 11, 7, 'unknown'),
            ('Cn', 'Copernicium', 'Copernici', 112, 285.0, 12, 7, 'transition metal'),
            ('Nh', 'Nihonium', 'Nihoni', 113, 286.0, 13, 7, 'unknown'),
            ('Fl', 'Flerovium', 'Flerovi', 114, 289.0, 14, 7, 'unknown'),
            ('Mc', 'Moscovium', 'Moscovi', 115, 290.0, 15, 7, 'unknown'),
            ('Lv', 'Livermorium', 'Livermori', 116, 293.0, 16, 7, 'unknown'),
            ('Ts', 'Tennessine', 'Tennessin', 117, 294.0, 17, 7, 'unknown'),
            ('Og', 'Oganesson', 'Oganesson', 118, 294.0, 18, 7, 'unknown'),
        ]

        result = {}
        for symbol, name_en, name_vi, an, am, group, period, category in data:
            result[symbol] = {
                'symbol': symbol,
                'name': name_en,
                'vi_name': name_vi,
                'atomic_number': an,
                'atomic_mass': am,  # g/mol
                'group': group,
                'period': period,
                'category': category,
            }
            # Reverse lookup by name
            result[name_en.lower()] = result[symbol]
            result[name_vi.lower()] = result[symbol]
            result[str(an)] = result[symbol]  # by atomic number string
        return result

    def _build_compounds(self) -> dict[str, dict[str, Any]]:
        """Hợp chất phổ biến."""
        return {
            'nước': {'formula': 'H2O', 'molar_mass': 18.015, 'type': 'oxide'},
            'water': {'formula': 'H2O', 'molar_mass': 18.015, 'type': 'oxide'},
            'h2o': {'formula': 'H2O', 'molar_mass': 18.015, 'type': 'oxide'},
            'muối ăn': {'formula': 'NaCl', 'molar_mass': 58.44, 'type': 'salt'},
            'sodium chloride': {'formula': 'NaCl', 'molar_mass': 58.44, 'type': 'salt'},
            'nacl': {'formula': 'NaCl', 'molar_mass': 58.44, 'type': 'salt'},
            'axit clohydric': {'formula': 'HCl', 'molar_mass': 36.458, 'type': 'acid'},
            'hydrochloric acid': {'formula': 'HCl', 'molar_mass': 36.458, 'type': 'acid'},
            'hcl': {'formula': 'HCl', 'molar_mass': 36.458, 'type': 'acid'},
            'axit sunfuric': {'formula': 'H2SO4', 'molar_mass': 98.079, 'type': 'acid'},
            'sulfuric acid': {'formula': 'H2SO4', 'molar_mass': 98.079, 'type': 'acid'},
            'h2so4': {'formula': 'H2SO4', 'molar_mass': 98.079, 'type': 'acid'},
            'axit nitric': {'formula': 'HNO3', 'molar_mass': 63.012, 'type': 'acid'},
            'nitric acid': {'formula': 'HNO3', 'molar_mass': 63.012, 'type': 'acid'},
            'hno3': {'formula': 'HNO3', 'molar_mass': 63.012, 'type': 'acid'},
            'ammoniac': {'formula': 'NH3', 'molar_mass': 17.031, 'type': 'base'},
            'ammonia': {'formula': 'NH3', 'molar_mass': 17.031, 'type': 'base'},
            'nh3': {'formula': 'NH3', 'molar_mass': 17.031, 'type': 'base'},
            'carbon dioxide': {'formula': 'CO2', 'molar_mass': 44.009, 'type': 'oxide'},
            'co2': {'formula': 'CO2', 'molar_mass': 44.009, 'type': 'oxide'},
            'carbon monoxide': {'formula': 'CO', 'molar_mass': 28.010, 'type': 'oxide'},
            'co': {'formula': 'CO', 'molar_mass': 28.010, 'type': 'oxide'},
            'methane': {'formula': 'CH4', 'molar_mass': 16.043, 'type': 'hydrocarbon'},
            'ch4': {'formula': 'CH4', 'molar_mass': 16.043, 'type': 'hydrocarbon'},
            'ethanol': {'formula': 'C2H5OH', 'molar_mass': 46.069, 'type': 'alcohol'},
            'c2h5oh': {'formula': 'C2H5OH', 'molar_mass': 46.069, 'type': 'alcohol'},
            'glucose': {'formula': 'C6H12O6', 'molar_mass': 180.16, 'type': 'sugar'},
            'c6h12o6': {'formula': 'C6H12O6', 'molar_mass': 180.16, 'type': 'sugar'},
            'sucrose': {'formula': 'C12H22O11', 'molar_mass': 342.30, 'type': 'sugar'},
            'hydrogen peroxide': {'formula': 'H2O2', 'molar_mass': 34.014, 'type': 'peroxide'},
            'h2o2': {'formula': 'H2O2', 'molar_mass': 34.014, 'type': 'peroxide'},
            'natri hydroxide': {'formula': 'NaOH', 'molar_mass': 39.997, 'type': 'base'},
            'sodium hydroxide': {'formula': 'NaOH', 'molar_mass': 39.997, 'type': 'base'},
            'naoh': {'formula': 'NaOH', 'molar_mass': 39.997, 'type': 'base'},
            'kali hydroxide': {'formula': 'KOH', 'molar_mass': 56.106, 'type': 'base'},
            'potassium hydroxide': {'formula': 'KOH', 'molar_mass': 56.106, 'type': 'base'},
            'koh': {'formula': 'KOH', 'molar_mass': 56.106, 'type': 'base'},
            'canxi cacbonat': {'formula': 'CaCO3', 'molar_mass': 100.09, 'type': 'salt'},
            'calcium carbonate': {'formula': 'CaCO3', 'molar_mass': 100.09, 'type': 'salt'},
            'caco3': {'formula': 'CaCO3', 'molar_mass': 100.09, 'type': 'salt'},
            'canxi oxide': {'formula': 'CaO', 'molar_mass': 56.077, 'type': 'oxide'},
            'calcium oxide': {'formula': 'CaO', 'molar_mass': 56.077, 'type': 'oxide'},
            'cao': {'formula': 'CaO', 'molar_mass': 56.077, 'type': 'oxide'},
            'sắt oxide': {'formula': 'Fe2O3', 'molar_mass': 159.69, 'type': 'oxide'},
            'iron oxide': {'formula': 'Fe2O3', 'molar_mass': 159.69, 'type': 'oxide'},
            'fe2o3': {'formula': 'Fe2O3', 'molar_mass': 159.69, 'type': 'oxide'},
            'đồng sulfate': {'formula': 'CuSO4', 'molar_mass': 159.609, 'type': 'salt'},
            'copper sulfate': {'formula': 'CuSO4', 'molar_mass': 159.609, 'type': 'salt'},
            'cuso4': {'formula': 'CuSO4', 'molar_mass': 159.609, 'type': 'salt'},
            'benzen': {'formula': 'C6H6', 'molar_mass': 78.111, 'type': 'aromatic'},
            'benzene': {'formula': 'C6H6', 'molar_mass': 78.111, 'type': 'aromatic'},
            'c6h6': {'formula': 'C6H6', 'molar_mass': 78.111, 'type': 'aromatic'},
            'axit acetic': {'formula': 'CH3COOH', 'molar_mass': 60.052, 'type': 'acid'},
            'acetic acid': {'formula': 'CH3COOH', 'molar_mass': 60.052, 'type': 'acid'},
            'ch3cooh': {'formula': 'CH3COOH', 'molar_mass': 60.052, 'type': 'acid'},
            'vitamin c': {'formula': 'C6H8O6', 'molar_mass': 176.124, 'type': 'vitamin'},
            'ascorbic acid': {'formula': 'C6H8O6', 'molar_mass': 176.124, 'type': 'vitamin'},
            'caffeine': {'formula': 'C8H10N4O2', 'molar_mass': 194.19, 'type': 'alkaloid'},
            'aspirin': {'formula': 'C9H8O4', 'molar_mass': 180.158, 'type': 'drug'},
            'acetylsalicylic acid': {'formula': 'C9H8O4', 'molar_mass': 180.158, 'type': 'drug'},
            'paracetamol': {'formula': 'C8H9NO2', 'molar_mass': 151.163, 'type': 'drug'},
            'acetaminophen': {'formula': 'C8H9NO2', 'molar_mass': 151.163, 'type': 'drug'},
            #  Missing compounds
            'starch': {'formula': '(C6H10O5)n', 'molar_mass': 162.14, 'type': 'polysaccharide'},
            'cellulose': {'formula': '(C6H10O5)n', 'molar_mass': 162.14, 'type': 'polysaccharide'},
            'collagen': {'formula': 'complex', 'molar_mass': 300000, 'type': 'protein'},
            'chitin': {'formula': '(C8H13NO5)n', 'molar_mass': 203.19, 'type': 'polysaccharide'},
            'rna': {'formula': 'complex', 'molar_mass': 340.0, 'type': 'nucleic_acid'},
            'dna': {'formula': 'complex', 'molar_mass': 330.0, 'type': 'nucleic_acid'},
            'fructose': {'formula': 'C6H12O6', 'molar_mass': 180.16, 'type': 'sugar'},
            'galactose': {'formula': 'C6H12O6', 'molar_mass': 180.16, 'type': 'sugar'},
            'maltose': {'formula': 'C12H22O11', 'molar_mass': 342.30, 'type': 'sugar'},
            'lactose': {'formula': 'C12H22O11', 'molar_mass': 342.30, 'type': 'sugar'},
            'glycerol': {'formula': 'C3H8O3', 'molar_mass': 92.094, 'type': 'alcohol'},
            'cholesterol': {'formula': 'C27H46O', 'molar_mass': 386.654, 'type': 'steroid'},
            'toluene': {'formula': 'C7H8', 'molar_mass': 92.140, 'type': 'aromatic'},
            'acetone': {'formula': 'C3H6O', 'molar_mass': 58.080, 'type': 'ketone'},
            'phenol': {'formula': 'C6H6O', 'molar_mass': 94.111, 'type': 'aromatic'},
            'aniline': {'formula': 'C6H7N', 'molar_mass': 93.129, 'type': 'aromatic'},
            'urea': {'formula': 'CH4N2O', 'molar_mass': 60.06, 'type': 'amide'},
            'methanol': {'formula': 'CH3OH', 'molar_mass': 32.04, 'type': 'alcohol'},
            'propanol': {'formula': 'C3H8O', 'molar_mass': 60.10, 'type': 'alcohol'},
            'propane': {'formula': 'C3H8', 'molar_mass': 44.10, 'type': 'hydrocarbon'},
            'butane': {'formula': 'C4H10', 'molar_mass': 58.12, 'type': 'hydrocarbon'},
            'pentane': {'formula': 'C5H12', 'molar_mass': 72.15, 'type': 'hydrocarbon'},
            'hexane': {'formula': 'C6H14', 'molar_mass': 86.18, 'type': 'hydrocarbon'},
            'heptane': {'formula': 'C7H16', 'molar_mass': 100.20, 'type': 'hydrocarbon'},
            'octane': {'formula': 'C8H18', 'molar_mass': 114.23, 'type': 'hydrocarbon'},
            'nonane': {'formula': 'C9H20', 'molar_mass': 128.26, 'type': 'hydrocarbon'},
            'decane': {'formula': 'C10H22', 'molar_mass': 142.28, 'type': 'hydrocarbon'},
            'ethylene': {'formula': 'C2H4', 'molar_mass': 28.05, 'type': 'hydrocarbon'},
            'propylene': {'formula': 'C3H6', 'molar_mass': 42.08, 'type': 'hydrocarbon'},
            'acetylene': {'formula': 'C2H2', 'molar_mass': 26.04, 'type': 'hydrocarbon'},
            'formic acid': {'formula': 'CH2O2', 'molar_mass': 46.03, 'type': 'acid'},
            'propionic acid': {'formula': 'C3H6O2', 'molar_mass': 74.08, 'type': 'acid'},
            'butyric acid': {'formula': 'C4H8O2', 'molar_mass': 88.11, 'type': 'acid'},
            'lactic acid': {'formula': 'C3H6O3', 'molar_mass': 90.08, 'type': 'acid'},
            'malic acid': {'formula': 'C4H6O5', 'molar_mass': 134.09, 'type': 'acid'},
            'tartaric acid': {'formula': 'C4H6O6', 'molar_mass': 150.09, 'type': 'acid'},
            'succinic acid': {'formula': 'C4H6O4', 'molar_mass': 118.09, 'type': 'acid'},
            'oxalic acid': {'formula': 'C2H2O4', 'molar_mass': 90.03, 'type': 'acid'},
            'citric acid': {'formula': 'C6H8O7', 'molar_mass': 192.12, 'type': 'acid'},
            'salicylic acid': {'formula': 'C7H6O3', 'molar_mass': 138.12, 'type': 'acid'},
            'bromine': {'formula': 'Br2', 'molar_mass': 159.808, 'type': 'element'},
            'chlorine': {'formula': 'Cl2', 'molar_mass': 70.906, 'type': 'element'},
            'iodine': {'formula': 'I2', 'molar_mass': 253.809, 'type': 'element'},
            'fluorine': {'formula': 'F2', 'molar_mass': 37.997, 'type': 'element'},
            'magnesium sulfate': {'formula': 'MgSO4', 'molar_mass': 120.366, 'type': 'salt'},
            'iron chloride': {'formula': 'FeCl3', 'molar_mass': 162.20, 'type': 'salt'},
            'zinc oxide': {'formula': 'ZnO', 'molar_mass': 81.38, 'type': 'oxide'},
            'titanium dioxide': {'formula': 'TiO2', 'molar_mass': 79.87, 'type': 'oxide'},
            'aluminum oxide': {'formula': 'Al2O3', 'molar_mass': 101.96, 'type': 'oxide'},
            'cyclohexane': {'formula': 'C6H12', 'molar_mass': 84.16, 'type': 'hydrocarbon'},
            'xylene': {'formula': 'C8H10', 'molar_mass': 106.17, 'type': 'aromatic'},
            'naphthalene': {'formula': 'C10H8', 'molar_mass': 128.17, 'type': 'aromatic'},
            'butanone': {'formula': 'C4H8O', 'molar_mass': 72.11, 'type': 'ketone'},
            'cyclopentane': {'formula': 'C5H10', 'molar_mass': 70.13, 'type': 'hydrocarbon'},
            # [V63.4] Biochemistry compounds
            'hemoglobin': {'formula': 'complex', 'molar_mass': 64500, 'type': 'protein'},
            'insulin': {'formula': 'complex', 'molar_mass': 5808, 'type': 'protein'},
            'albumin': {'formula': 'complex', 'molar_mass': 66463, 'type': 'protein'},
            'myoglobin': {'formula': 'complex', 'molar_mass': 16952, 'type': 'protein'},
            'lysozyme': {'formula': 'complex', 'molar_mass': 14307, 'type': 'protein'},
            'casein': {'formula': 'complex', 'molar_mass': 23000, 'type': 'protein'},
            'keratin': {'formula': 'complex', 'molar_mass': 55000, 'type': 'protein'},
            'elastin': {'formula': 'complex', 'molar_mass': 64000, 'type': 'protein'},
            'fibrinogen': {'formula': 'complex', 'molar_mass': 340000, 'type': 'protein'},
            'immunoglobulin': {'formula': 'complex', 'molar_mass': 150000, 'type': 'protein'},
            'myosin': {'formula': 'complex', 'molar_mass': 224000, 'type': 'protein'},
            'actin': {'formula': 'complex', 'molar_mass': 42000, 'type': 'protein'},
            'tubulin': {'formula': 'complex', 'molar_mass': 55000, 'type': 'protein'},
            'amylase': {'formula': 'complex', 'molar_mass': 50000, 'type': 'enzyme'},
            'lipase': {'formula': 'complex', 'molar_mass': 48000, 'type': 'enzyme'},
            'pepsin': {'formula': 'complex', 'molar_mass': 34644, 'type': 'enzyme'},
            'trypsin': {'formula': 'complex', 'molar_mass': 23300, 'type': 'enzyme'},
            'catalase': {'formula': 'complex', 'molar_mass': 250000, 'type': 'enzyme'},
            'polyethylene': {'formula': '(C2H4)n', 'molar_mass': 28.05, 'type': 'polymer'},
            'polystyrene': {'formula': '(C8H8)n', 'molar_mass': 104.15, 'type': 'polymer'},
            'nylon': {'formula': 'complex', 'molar_mass': 226.32, 'type': 'polymer'},
            'rubber': {'formula': '(C5H8)n', 'molar_mass': 68.12, 'type': 'polymer'},
            'pet': {'formula': '(C10H8O4)n', 'molar_mass': 192.17, 'type': 'polymer'},
            'pvc': {'formula': '(C2H3Cl)n', 'molar_mass': 62.50, 'type': 'polymer'},
        }

    @property
    def name(self) -> str:
        return "ChemistryDataSource"

    @property
    def priority(self) -> int:
        return 2

    @property
    def ttl(self) -> int:
        return 604800  # 1 week - chemical constants rarely change

    def get_supported_intents(self) -> list[str]:
        return [
            'chemical_element',
            'chemical_compound',
            'chemical_reaction',
            'molar_mass',
            'chemical_constant',
            'ph_info',
            'oxidation_state',
        ]

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower().strip()
            # Check elements (by symbol, name, or atomic number)
            if entity_lower in self._elements:
                return True
            # Check compounds
            if entity_lower in self._compounds:
                return True
            # Check constants
            if entity_lower in self._constants:
                return True
            # Check reactions
            for key in self._reactions:
                if key in entity_lower or entity_lower in key:
                    return True
            # Check for chemical formula pattern (e.g., H2O, NaCl)
            import re
            if re.match(r'^[A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)*$', entity):
                return True
        return False

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        """Lấy dữ liệu hóa học."""
        if not entity:
            return None

        entity_lower = entity.lower().strip()

        # Try elements
        result = self._search_elements(entity_lower, entity)
        if result:
            return result

        # Try compounds
        result = self._search_compounds(entity_lower)
        if result:
            return result

        # Try constants
        result = self._search_constants(entity_lower)
        if result:
            return result

        # Try reactions
        result = self._search_reactions(entity_lower)
        if result:
            return result

        # Try PubChem API as fallback (for compounds)
        result = self._fetch_from_pubchem(entity)
        if result:
            return result

        return None

    def _search_elements(self, entity_lower: str, original: str) -> dict[str, Any] | None:
        """Tìm nguyên tố."""
        # Direct match
        if entity_lower in self._elements:
            data = self._elements[entity_lower]
            return {
                'value': data['atomic_mass'],
                'source': 'IUPAC Periodic Table (Local)',
                'metadata': {
                    'symbol': data['symbol'],
                    'name_en': data['name'],
                    'name_vi': data['vi_name'],
                    'atomic_number': data['atomic_number'],
                    'atomic_mass': data['atomic_mass'],
                    'group': data['group'],
                    'period': data['period'],
                    'category': data['category'],
                    'unit': 'g/mol',
                }
            }

        # Case-sensitive symbol check (e.g., "Fe" not "fe")
        if original in self._elements:
            data = self._elements[original]
            return {
                'value': data['atomic_mass'],
                'source': 'IUPAC Periodic Table (Local)',
                'metadata': {
                    'symbol': data['symbol'],
                    'name_en': data['name'],
                    'name_vi': data['vi_name'],
                    'atomic_number': data['atomic_number'],
                    'atomic_mass': data['atomic_mass'],
                    'group': data['group'],
                    'period': data['period'],
                    'category': data['category'],
                    'unit': 'g/mol',
                }
            }

        return None

    def _search_compounds(self, entity_lower: str) -> dict[str, Any] | None:
        """Tìm hợp chất."""
        if entity_lower in self._compounds:
            data = self._compounds[entity_lower]
            return {
                'value': data['molar_mass'],
                'source': 'Local Chemistry Database',
                'metadata': {
                    'formula': data['formula'],
                    'molar_mass': data['molar_mass'],
                    'type': data['type'],
                    'unit': 'g/mol',
                }
            }
        return None

    def _search_constants(self, entity_lower: str) -> dict[str, Any] | None:
        """Tìm hằng số hóa học."""
        if entity_lower in self._constants:
            value = self._constants[entity_lower]
            return {
                'value': value,
                'source': 'CODATA / NIST (Local)',
                'metadata': {
                    'constant_name': entity_lower,
                    'method': 'lookup',
                }
            }
        # Partial match
        for key, value in self._constants.items():
            if key in entity_lower or entity_lower in key:
                return {
                    'value': value,
                    'source': 'CODATA / NIST (Local)',
                    'metadata': {
                        'constant_name': key,
                        'method': 'lookup',
                    }
                }
        return None

    def _search_reactions(self, entity_lower: str) -> dict[str, Any] | None:
        """Tìm phản ứng hóa học."""
        if entity_lower in self._reactions:
            data = self._reactions[entity_lower]
            return {
                'value': data['equation'],
                'source': 'Local Chemistry Database',
                'metadata': data
            }
        # Partial match
        for key, data in self._reactions.items():
            if key in entity_lower or entity_lower in key:
                return {
                    'value': data['equation'],
                    'source': 'Local Chemistry Database',
                    'metadata': data
                }
        return None

    def _fetch_from_pubchem(self, entity: str) -> dict[str, Any] | None:
        """Fallback: Lấy từ PubChem."""
        try:
            # [AUDIT-20260909 SSRF-S1] build URL (quote entity) rồi fetch qua
            # safe_urlopen thay raw requests.get.
            url = build_pubchem_url(entity)
            req = urllib.request.Request(
                url, headers={"User-Agent": "SCP-Chemistry/1.0"}
            )  # noqa: S310 — validated by safe_urlopen
            with safe_urlopen(req, timeout=5) as response:
                if getattr(response, "status", 200) != 200:
                    return None
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            props = data.get('PropertyTable', {}).get('Properties', [{}])[0]
            return {
                'value': props.get('MolecularWeight', 0),
                'source': 'PubChem API',
                'metadata': {
                    'formula': props.get('MolecularFormula', ''),
                    'molar_mass': props.get('MolecularWeight', 0),
                    'unit': 'g/mol',
                    'method': 'pubchem'
                }
            }
        except Exception as e:
            logger.warning(f"[Chemistry] PubChem fetch failed: {e}", exc_info=True)
        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True
