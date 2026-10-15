"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.

WHY Engine, Recursive Why, MetaFalsifier, ProofGraph
License: See LICENSE file
"""

"""
 TechnologyDataSource — Công nghệ & Kỹ thuật
Bao gồm: programming languages, AI/ML concepts, hardware, internet protocols.
Fallback: LiveKnowledgeFetcher (arXiv + Wikipedia).
"""
import logging
from typing import Any

from scp.interfaces.data_source import IDataSource

logger = logging.getLogger(__name__)


class TechnologyDataSource(IDataSource):
    """Data source cho Công nghệ & Kỹ thuật."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

        # Programming languages
        self._languages = {
            'python': {'year': 1991, 'creator': 'Guido van Rossum',
                       'paradigm': 'Multi-paradigm', 'typing': 'Dynamic',
                       'use_cases': ['AI/ML', 'Web', 'Data Science', 'Automation']},
            'javascript': {'year': 1995, 'creator': 'Brendan Eich',
                           'paradigm': 'Multi-paradigm', 'typing': 'Dynamic',
                           'use_cases': ['Web frontend', 'Node.js backend', 'Mobile']},
            'java': {'year': 1995, 'creator': 'James Gosling',
                     'paradigm': 'OOP', 'typing': 'Static',
                     'use_cases': ['Enterprise', 'Android', 'Backend']},
            'c': {'year': 1972, 'creator': 'Dennis Ritchie',
                  'paradigm': 'Procedural', 'typing': 'Static',
                  'use_cases': ['System', 'Embedded', 'OS']},
            'c++': {'year': 1985, 'creator': 'Bjarne Stroustrup',
                    'paradigm': 'Multi-paradigm', 'typing': 'Static',
                    'use_cases': ['Game', 'System', 'Performance-critical']},
            'c#': {'year': 2000, 'creator': 'Microsoft',
                   'paradigm': 'Multi-paradigm', 'typing': 'Static',
                   'use_cases': ['.NET', 'Game (Unity)', 'Enterprise']},
            'go': {'year': 2009, 'creator': 'Google',
                   'paradigm': 'Concurrent', 'typing': 'Static',
                   'use_cases': ['Backend', 'Microservices', 'DevOps']},
            'rust': {'year': 2010, 'creator': 'Mozilla',
                     'paradigm': 'Multi-paradigm', 'typing': 'Static',
                     'use_cases': ['System', 'WebAssembly', 'Performance']},
            'php': {'year': 1995, 'creator': 'Rasmus Lerdorf',
                    'paradigm': 'Multi-paradigm', 'typing': 'Dynamic',
                    'use_cases': ['Web backend']},
            'ruby': {'year': 1995, 'creator': 'Yukihiro Matsumoto',
                     'paradigm': 'OOP', 'typing': 'Dynamic',
                     'use_cases': ['Web (Rails)']},
            'swift': {'year': 2014, 'creator': 'Apple',
                      'paradigm': 'Multi-paradigm', 'typing': 'Static',
                      'use_cases': ['iOS', 'macOS']},
            'kotlin': {'year': 2011, 'creator': 'JetBrains',
                       'paradigm': 'Multi-paradigm', 'typing': 'Static',
                       'use_cases': ['Android', 'Backend']},
            'typescript': {'year': 2012, 'creator': 'Microsoft',
                           'paradigm': 'Multi-paradigm', 'typing': 'Static',
                           'use_cases': ['Web', 'Node.js']},
            'sql': {'year': 1974, 'creator': 'IBM',
                    'paradigm': 'Declarative', 'typing': 'Static',
                    'use_cases': ['Database']},
            'html': {'year': 1993, 'creator': 'Tim Berners-Lee',
                     'paradigm': 'Markup', 'typing': 'N/A',
                     'use_cases': ['Web structure']},
        }

        # AI/ML concepts
        self._ai_concepts = {
            'machine learning': {'vi': 'Học máy',
                                 'desc': 'AI subset, học từ data không cần program explicit',
                                 'types': ['Supervised', 'Unsupervised', 'Reinforcement']},
            'deep learning': {'vi': 'Học sâu',
                              'desc': 'ML dùng neural network nhiều lớp',
                              'types': ['CNN', 'RNN', 'LSTM', 'Transformer']},
            'neural network': {'vi': 'Mạng nơ-ron nhân tạo',
                               'desc': 'Mô phỏng nơ-ron sinh học',
                               'components': ['input layer', 'hidden layers', 'output layer']},
            'transformer': {'vi': 'Kiến trúc Transformer',
                            'desc': 'Architecture dùng attention mechanism',
                            'year': 2017, 'paper': 'Attention Is All You Need'},
            'llm': {'vi': 'Large Language Model',
                    'desc': 'Mô hình ngôn ngữ lớn (GPT, BERT, LLaMA)',
                    'examples': ['GPT-4', 'BERT', 'LLaMA', 'Claude']},
            'gpt': {'vi': 'Generative Pre-trained Transformer',
                    'desc': 'Họ mô hình của OpenAI',
                    'versions': ['GPT-1', 'GPT-2', 'GPT-3', 'GPT-4']},
            'bert': {'vi': 'Bidirectional Encoder Representations from Transformers',
                     'desc': 'Mô hình của Google cho NLP',
                     'year': 2018},
            'rag': {'vi': 'Retrieval-Augmented Generation',
                    'desc': 'Kết hợp retrieval và generation để giảm hallucination'},
            'cnn': {'vi': 'Convolutional Neural Network',
                    'desc': 'Cho image processing',
                    'use_cases': ['Image classification', 'Object detection']},
            'rnn': {'vi': 'Recurrent Neural Network',
                    'desc': 'Cho sequence data',
                    'use_cases': ['NLP', 'Time series']},
            'gan': {'vi': 'Generative Adversarial Network',
                    'desc': 'Hai mạng: generator và discriminator',
                    'use_cases': ['Image generation', 'Deepfake']},
            'reinforcement learning': {'vi': 'Học tăng cường',
                                       'desc': 'Học qua trial-and-error với rewards'},
        }

        # Hardware specs
        self._hardware = {
            'cpu': {'vi': 'Bộ xử lý trung tâm', 'desc': 'Central Processing Unit'},
            'gpu': {'vi': 'Bộ xử lý đồ họa', 'desc': 'Graphics Processing Unit, dùng cho AI/rendering'},
            'ram': {'vi': 'Bộ nhớ truy cập ngẫu nhiên', 'desc': 'Random Access Memory'},
            'ssd': {'vi': 'Ổ cứng thể rắn', 'desc': 'Solid State Drive'},
            'hdd': {'vi': 'Ổ cứng từ', 'desc': 'Hard Disk Drive'},
            'motherboard': {'vi': 'Bo mạch chủ', 'desc': 'Main circuit board'},
            'psu': {'vi': 'Nguồn máy', 'desc': 'Power Supply Unit'},
            'nic': {'vi': 'Card mạng', 'desc': 'Network Interface Card'},
        }

        # Internet protocols
        self._protocols = {
            'http': {'port': 80, 'layer': 'Application', 'desc': 'HyperText Transfer Protocol'},
            'https': {'port': 443, 'layer': 'Application', 'desc': 'HTTP Secure (TLS/SSL)'},
            'ftp': {'port': 21, 'layer': 'Application', 'desc': 'File Transfer Protocol'},
            'ssh': {'port': 22, 'layer': 'Application', 'desc': 'Secure Shell'},
            'smtp': {'port': 25, 'layer': 'Application', 'desc': 'Simple Mail Transfer Protocol'},
            'dns': {'port': 53, 'layer': 'Application', 'desc': 'Domain Name System'},
            'tcp': {'port': 'N/A', 'layer': 'Transport', 'desc': 'Transmission Control Protocol'},
            'udp': {'port': 'N/A', 'layer': 'Transport', 'desc': 'User Datagram Protocol'},
            'ip': {'port': 'N/A', 'layer': 'Network', 'desc': 'Internet Protocol'},
            'dhcp': {'port': 67, 'layer': 'Application', 'desc': 'Dynamic Host Config Protocol'},
        }

        # Tech companies (founding year)
        self._companies = {
            'google': {'founded': 1998, 'founders': 'Larry Page, Sergey Brin'},
            'microsoft': {'founded': 1975, 'founders': 'Bill Gates, Paul Allen'},
            'apple': {'founded': 1976, 'founders': 'Steve Jobs, Steve Wozniak, Ronald Wayne'},
            'amazon': {'founded': 1994, 'founders': 'Jeff Bezos'},
            'facebook': {'founded': 2004, 'founders': 'Mark Zuckerberg'},
            'meta': {'founded': 2004, 'founders': 'Mark Zuckerberg', 'note': 'Đổi tên từ Facebook 2021'},
            'netflix': {'founded': 1997, 'founders': 'Reed Hastings, Marc Randolph'},
            'tesla': {'founded': 2003, 'founders': 'Elon Musk, Martin Eberhard, Marc Tarpenning'},
            'openai': {'founded': 2015, 'founders': 'Sam Altman, Elon Musk, Ilya Sutskever, Greg Brockman'},
            'nvidia': {'founded': 1993, 'founders': 'Jensen Huang, Chris Malachowsky, Curtis Priem'},
            'intel': {'founded': 1968, 'founders': 'Robert Noyce, Gordon Moore'},
            'samsung': {'founded': 1938, 'founders': 'Lee Byung-chul'},
            'sony': {'founded': 1946, 'founders': 'Masaru Ibuka, Akio Morita'},
        }

    @property
    def name(self) -> str:
        return "TechnologyDataSource"

    @property
    def priority(self) -> int:
        return 2

    @property
    def ttl(self) -> int:
        return 2592000  # 30 days

    def get_supported_intents(self) -> list[str]:
        return ['tech_language', 'tech_ai', 'tech_hardware',
                'tech_protocol', 'tech_company', 'tech_info']

    def can_handle(self, intent: str, entity: str | None = None) -> bool:
        if intent in self.get_supported_intents():
            return True
        if entity:
            entity_lower = entity.lower().strip()
            for table in (self._languages, self._ai_concepts, self._hardware,
                          self._protocols, self._companies):
                if entity_lower in table:
                    return True
                for key in table:
                    if key in entity_lower or entity_lower in key:
                        return True
        return False

    def fetch(self, intent: str, entity: str, **kwargs) -> dict[str, Any] | None:
        if not entity:
            return None
        entity_lower = entity.lower().strip()

        # [V63 FIX] First pass: EXACT match only (prevents "go" matching "google")
        for table_name, table in [
            ('language', self._languages),
            ('ai_concept', self._ai_concepts),
            ('hardware', self._hardware),
            ('protocol', self._protocols),
            ('company', self._companies),
        ]:
            if entity_lower in table:
                data = table[entity_lower]
                # [V63.1] Build value from ALL available fields, not just desc
                parts = []
                for key in ['desc', 'vi', 'year', 'founded', 'creator', 'founders',
                            'paradigm', 'typing', 'use_cases', 'port', 'layer',
                            'specialty', 'period', 'origin']:
                    if key in data:
                        val = data[key]
                        if isinstance(val, list):
                            val = ', '.join(str(v) for v in val)
                        parts.append(f"{key}={val}")
                value = '; '.join(parts) if parts else ''
                return {
                    'value': value,
                    'source': 'Local Technology Database',
                    'metadata': {**data, 'category': table_name}
                }

        #  Second pass: partial match — but ONLY if entity is longer than key
        # This prevents "go" (2 chars) matching "google" (6 chars)
        for table_name, table in [
            ('language', self._languages),
            ('ai_concept', self._ai_concepts),
            ('hardware', self._hardware),
            ('protocol', self._protocols),
            ('company', self._companies),
        ]:
            for key, data in table.items():
                #  Only match if key is substantial (>= 4 chars) and entity contains key
                # OR entity is contained in key (entity="python" in key="python language")
                if len(key) >= 4 and key in entity_lower:
                    return {
                        'value': str(data.get('desc', data.get('vi', data.get('year', '')))),
                        'source': 'Local Technology Database',
                        'metadata': {**data, 'category': table_name, 'matched_key': key}
                    }
                if entity_lower in key and len(entity_lower) >= 4:
                    return {
                        'value': str(data.get('desc', data.get('vi', data.get('year', '')))),
                        'source': 'Local Technology Database',
                        'metadata': {**data, 'category': table_name, 'matched_key': key}
                    }

        return None

    def health_check(self) -> bool:
        """[V104.32] Always-healthy THEO THIẾT KẾ: source thuần local
        (dataset cứng trong code, fetch() không chạm mạng) — không có
        network endpoint nào để ping, nên không có live evidence để thu.
        Contract: KHÔNG dùng nguồn này làm bằng chứng reachable cho bất
        kỳ network capability nào."""
        return True
