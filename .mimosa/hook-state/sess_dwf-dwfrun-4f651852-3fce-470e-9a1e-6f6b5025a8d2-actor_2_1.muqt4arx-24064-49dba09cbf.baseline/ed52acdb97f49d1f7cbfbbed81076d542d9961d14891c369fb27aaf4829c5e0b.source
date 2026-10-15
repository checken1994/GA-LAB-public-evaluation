"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
Data Sources Package (V96 - 45 sources)
=================================================================

Core sources (V44-V96):
  Math, Logic, Statistics, Physics, Chemistry, Astronomy, Biology,
  Geography, History, Weather, Finance, Conversion, Reality

Domain sources (V46-V96):
  Medical, Technology, Sports, Legal, Arts, Education, Architecture,
  Agriculture, Environment, Tourism, Energy, Transport, FoodTech,
  Aerospace, Blockchain, Cybersecurity, GenAI, UXUI, DigitalMarketing,
  Ecommerce, Psychology, AudioVideo, Heritage, Diplomacy, Religion,
  Crafts, Military, Social, SpaceMedicine, Oceanography, Cartography,
  Geology, AudioVideo, Government

Dynamic fetcher:
  LiveKnowledgeFetcher (RAG via Wikipedia/Wikidata/arXiv/DuckDuckGo)

Usage:
    from scp.data_sources import get_registry, register_all_sources
"""
# [V5.8-API] NEW agriculture data source — USDA NASS QuickStats + local DB fallback
import logging

# [V5.9-WIRE] Auto-wired 25 orphaned data sources
from .aerospace import AerospaceDataSource
from .agriculture import AgricultureDataSource

# [Task 32-A] 16 new DataSources registered (6 from fix17-18 + 10 from fix19).
# Previously created but NOT imported in __init__.py → unreachable from
# register_all_sources() + SmartClassifier routing. Now wired in.
# --- fix17-18 batch (6) ---
from .alphavantage import AlphaVantageDataSource
from .architecture import ArchitectureDataSource
from .arts import ArtsDataSource
from .astronomy import AstronomyDataSource
from .audiovideo import AudioVideoDataSource
from .biology import BiologyDataSource  # [BUGFIX] was in __all__ but never imported (ruff F822 caught this)
from .blockchain import BlockchainDataSource
from .cartography import CartographyDataSource

# V44 core sources
from .chemistry import ChemistryDataSource
from .conversion import ConversionDataSource

# --- fix19 batch (10) ---
from .cornell_lii import CornellLIIDataSource
from .courtlistener import CourtListenerDataSource
from .crafts import CraftsDataSource
from .cybersecurity import CybersecurityDataSource
from .digitalmarketing import DigitalMarketingDataSource
from .diplomacy import DiplomacyDataSource
from .domain_classifier import classify_question, classify_top1

# V96 infrastructure
from .domain_registry import DOMAINS, get_domain, list_domains
from .domain_registry import get_stats as registry_stats
from .dtic import DTICDataSource
from .ecommerce import EcommerceDataSource
from .education import EducationDataSource
from .energy import EnergyDataSource
from .environment import EnvironmentDataSource
from .eric import ERICDataSource
from .finance import FinanceDataSource
from .foodtech import FoodTechDataSource
from .fred import FREDDataSource
from .genai import GenAIDataSource
from .geography import GeographyDataSource
from .geology import GeologyDataSource
from .glottolog import GlottologDataSource

# [Task 34-A / OPT-15] Google Fact Check API — created in Task 33-A but never
# registered in __init__.py, making it unreachable from register_all_sources()
# and SmartClassifier routing. Now wired in (additive — no existing source
# touched). DNA SCP #6 Evidence: aggregates 40k+ fact checks from 100+
# publishers (Snopes, PolitiFact, FactCheck.org, Reuters, etc.).
from .google_factcheck import GoogleFactCheckDataSource
from .gutenberg import GutenbergDataSource

# V46-V96 new sources
from .heritage import HeritageDataSource
from .history import HistoryDataSource
from .legal import LegalDataSource
from .live_knowledge import clear_expired_cache, fetch_live, get_cache_stats
from .logic import LogicDataSource
from .math import MathDataSource

# V46 new sources
from .medical import MedicalDataSource
from .metmuseum import MetMuseumDataSource
from .military import MilitaryDataSource
from .newsapi import NewsAPIDataSource
from .noaa import NOAADataSource
from .oceanography import OceanographyDataSource
from .physics import PhysicsDataSource  # [BUGFIX] was in __all__ but never imported (ruff F822 caught this)
from .psychology import PsychologyDataSource
from .reality import RealityDataSource
from .registry import DataSourceRegistry, get_registry
from .religion import ReligionDataSource
from .social import SocialDataSource
from .spacemedicine import SpaceMedicineDataSource
from .sports import SportsDataSource
from .statistics import StatisticsDataSource  # [BUGFIX] was in __all__ but never imported (ruff F822 caught this)
from .technology import TechnologyDataSource
from .tourism import TourismDataSource
from .transport import TransportDataSource
from .undata import UNDataDataSource
from .unesco import UNESCODataSource
from .usgs import USGSDataSource
from .uxui import UXUIDataSource
from .weather import WeatherDataSource
from .wikiart import WikiArtDataSource
from .worldbank import WorldBankDataSource

logger = logging.getLogger(__name__)


def register_all_sources(registry: DataSourceRegistry = None) -> DataSourceRegistry:
    """
    Đăng ký tất cả 34 data sources (13 V44/V46 + 5 V5.8 + 16 fix17-19).
    LiveKnowledgeFetcher không register như data source — gọi trực tiếp.

    [Task 32-A] Added 16 new DataSources (alphavantage, newsapi, fred,
    worldbank, gutenberg, eric, cornell_lii, courtlistener, unesco, dtic,
    metmuseum, wikiart, noaa, usgs, undata, glottolog) — were created but
    never registered, making them dead code. Now wired into the registry.
    """
    if registry is None:
        registry = get_registry()

    sources = [
        # V44 core (8)
        ChemistryDataSource(),
        AstronomyDataSource(),
        GeographyDataSource(),
        HistoryDataSource(),
        WeatherDataSource(),
        FinanceDataSource(),
        ConversionDataSource(),
        RealityDataSource(),
        # V46 new (5)
        MedicalDataSource(),
        TechnologyDataSource(),
        SportsDataSource(),
        LegalDataSource(),
        ArtsDataSource(),
        # [V5.8-API] NEW data source (was missing in v5.7)
        AgricultureDataSource(),
        # [Task 32-A] fix17-18 batch (6) — finance/news/literature/education
        AlphaVantageDataSource(),
        NewsAPIDataSource(),
        FREDDataSource(),
        WorldBankDataSource(),
        GutenbergDataSource(),
        ERICDataSource(),
        # [Task 32-A] fix19 batch (10) — law/education/art/earth_science/
        # military/linguistics/political_science
        CornellLIIDataSource(),
        CourtListenerDataSource(),
        UNESCODataSource(),
        DTICDataSource(),
        MetMuseumDataSource(),
        WikiArtDataSource(),
        NOAADataSource(),
        USGSDataSource(),
        UNDataDataSource(),
        GlottologDataSource(),
        # [Task 34-A / OPT-15] Fact-checking source — disabled until
        # GOOGLE_FACT_CHECK_API_KEY is provisioned (constructor reads env
        # var and sets self.enabled accordingly). Registering it now makes it
        # discoverable by SmartClassifier routing + AsyncMultiSourceVerifier.
        GoogleFactCheckDataSource(),
        # [V5.9-WIRE] Wired 25 orphaned sources
        AerospaceDataSource(),
        ArchitectureDataSource(),
        AudioVideoDataSource(),
        BlockchainDataSource(),
        CartographyDataSource(),
        CraftsDataSource(),
        CybersecurityDataSource(),
        DigitalMarketingDataSource(),
        DiplomacyDataSource(),
        EcommerceDataSource(),
        EducationDataSource(),
        EnergyDataSource(),
        EnvironmentDataSource(),
        FoodTechDataSource(),
        GenAIDataSource(),
        GeologyDataSource(),
        LogicDataSource(),
        OceanographyDataSource(),
        PsychologyDataSource(),
        ReligionDataSource(),
        SocialDataSource(),
        SpaceMedicineDataSource(),
        TourismDataSource(),
        TransportDataSource(),
        UXUIDataSource(),

    ]

    for src in sources:
        try:
            registry.register(src)
        except Exception as e:
            logger.warning(f"[INIT] Failed to register {src.name}: {e}", exc_info=True)

    return registry


__all__ = [

    # [V5.9-WIRE] Wired 25 orphaned sources
    'AerospaceDataSource', 'ArchitectureDataSource', 'AudioVideoDataSource', 'BlockchainDataSource', 'CartographyDataSource', 'CraftsDataSource', 'CybersecurityDataSource', 'DigitalMarketingDataSource', 'DiplomacyDataSource', 'EcommerceDataSource', 'EducationDataSource', 'EnergyDataSource', 'EnvironmentDataSource', 'FoodTechDataSource', 'GenAIDataSource', 'GeologyDataSource', 'LogicDataSource', 'OceanographyDataSource', 'PsychologyDataSource', 'ReligionDataSource', 'SocialDataSource', 'SpaceMedicineDataSource', 'TourismDataSource', 'TransportDataSource', 'UXUIDataSource',
    # Registry
    'DataSourceRegistry', 'get_registry', 'register_all_sources',
    # V44-V96 sources (45 total)
    'ChemistryDataSource', 'AstronomyDataSource',
    'GeographyDataSource', 'HistoryDataSource',
    'StatisticsDataSource', 'MathDataSource',
    'WeatherDataSource', 'FinanceDataSource', 'ConversionDataSource',
    'RealityDataSource', 'PhysicsDataSource', 'BiologyDataSource',
    # V46-V96 domain sources
    'MedicalDataSource', 'TechnologyDataSource', 'SportsDataSource',
    'LegalDataSource', 'ArtsDataSource', 'HeritageDataSource',
    'MilitaryDataSource',
    # [V5.8-API] NEW
    'AgricultureDataSource',
    # [Task 32-A] fix17-18 batch (6)
    'AlphaVantageDataSource', 'NewsAPIDataSource', 'FREDDataSource',
    'WorldBankDataSource', 'GutenbergDataSource', 'ERICDataSource',
    # [Task 32-A] fix19 batch (10)
    'CornellLIIDataSource', 'CourtListenerDataSource', 'UNESCODataSource',
    'DTICDataSource', 'MetMuseumDataSource', 'WikiArtDataSource',
    'NOAADataSource', 'USGSDataSource', 'UNDataDataSource',
    'GlottologDataSource',
    # [Task 34-A / OPT-15] Fact-checking
    'GoogleFactCheckDataSource',
    # V96 infrastructure
    'DOMAINS', 'get_domain', 'list_domains', 'registry_stats',
    'classify_question', 'classify_top1',
    'fetch_live', 'get_cache_stats', 'clear_expired_cache',
]

