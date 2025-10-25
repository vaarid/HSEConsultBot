"""
Модуль для работы с базой знаний FAQ по охране труда
"""
import json
import aiohttp
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

from utils.logger import setup_logger

logger = setup_logger()


class KnowledgeBase:
    """
    Класс для работы с базой знаний FAQ
    """
    
    def __init__(self, faq_file_path: str = "faq_ohs_ru_links.json"):
        """
        Инициализация базы знаний
        
        Args:
            faq_file_path: Путь к файлу с FAQ
        """
        self.faq_file_path = Path(faq_file_path)
        self.faq_data: List[Dict] = []
        self._load_faq()
    
    def _load_faq(self):
        """
        Загрузить FAQ из JSON файла
        """
        try:
            if not self.faq_file_path.exists():
                logger.error(f"Файл FAQ не найден: {self.faq_file_path}")
                return
            
            with open(self.faq_file_path, 'r', encoding='utf-8') as f:
                self.faq_data = json.load(f)
            
            logger.info(f"Загружено {len(self.faq_data)} вопросов из базы знаний")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке FAQ: {e}", exc_info=True)
    
    def reload_faq(self):
        """
        Перезагрузить FAQ из файла
        """
        logger.info("Перезагрузка базы знаний FAQ")
        self._load_faq()
    
    def get_all_questions(self) -> List[str]:
        """
        Получить список всех вопросов
        
        Returns:
            List[str]: Список вопросов
        """
        return [item['question'] for item in self.faq_data]
    
    def get_blocks(self) -> List[str]:
        """
        Получить список уникальных блоков (категорий)
        
        Returns:
            List[str]: Список блоков
        """
        blocks = set(item['block'] for item in self.faq_data)
        return sorted(blocks)
    
    def get_questions_by_block(self, block_name: str) -> List[Dict]:
        """
        Получить вопросы по конкретному блоку
        
        Args:
            block_name: Название блока
            
        Returns:
            List[Dict]: Список вопросов в блоке
        """
        return [
            item for item in self.faq_data 
            if item['block'] == block_name
        ]
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Рассчитать схожесть двух текстов (простой метод)
        
        Args:
            text1: Первый текст
            text2: Второй текст
            
        Returns:
            float: Коэффициент схожести (0-1)
        """
        # Приводим к нижнему регистру
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # Используем SequenceMatcher для базового сравнения
        similarity = SequenceMatcher(None, text1_lower, text2_lower).ratio()
        
        # Дополнительный бонус за совпадение ключевых слов
        words1 = set(text1_lower.split())
        words2 = set(text2_lower.split())
        
        # Убираем стоп-слова
        stop_words = {'что', 'как', 'где', 'когда', 'кто', 'какой', 'какая', 
                      'какие', 'нужно', 'можно', 'ли', 'в', 'на', 'по', 'с', 
                      'и', 'или', 'а', 'но', 'это', 'то', 'да', 'нет', 'для',
                      'при', 'о', 'об', 'от', 'до', 'из', 'у', 'к'}
        
        words1_filtered = words1 - stop_words
        words2_filtered = words2 - stop_words
        
        if words1_filtered and words2_filtered:
            # Jaccard similarity для ключевых слов
            intersection = len(words1_filtered & words2_filtered)
            union = len(words1_filtered | words2_filtered)
            keyword_similarity = intersection / union if union > 0 else 0
            
            # Комбинируем оба метода
            similarity = (similarity * 0.6) + (keyword_similarity * 0.4)
        
        return similarity
    
    def find_relevant_questions(
        self, 
        query: str, 
        threshold: float = 0.5, 
        top_k: int = 5
    ) -> List[Tuple[Dict, float]]:
        """
        Найти релевантные вопросы из базы знаний
        
        Args:
            query: Запрос пользователя
            threshold: Минимальный порог схожести (0-1)
            top_k: Количество топ результатов
            
        Returns:
            List[Tuple[Dict, float]]: Список кортежей (вопрос, оценка схожести)
        """
        if not self.faq_data:
            logger.warning("База знаний пуста")
            return []
        
        # Рассчитываем схожесть для каждого вопроса
        similarities = []
        
        for item in self.faq_data:
            question = item['question']
            similarity = self._calculate_similarity(query, question)
            
            if similarity >= threshold:
                similarities.append((item, similarity))
        
        # Сортируем по убыванию схожести
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Возвращаем топ-k результатов
        return similarities[:top_k]
    
    async def check_url_validity(self, url: str, timeout: int = 5) -> Tuple[bool, Optional[int]]:
        """
        Проверить актуальность URL (доступность)
        
        Args:
            url: URL для проверки
            timeout: Таймаут запроса в секундах
            
        Returns:
            Tuple[bool, Optional[int]]: (доступен, статус-код)
        """
        if not url or url.strip() == "":
            return False, None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    allow_redirects=True
                ) as response:
                    # Считаем URL валидным, если статус 200-399
                    is_valid = 200 <= response.status < 400
                    return is_valid, response.status
                    
        except aiohttp.ClientError as e:
            logger.warning(f"Ошибка при проверке URL {url}: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке URL {url}: {e}")
            return False, None
    
    async def get_answer_with_validation(
        self, 
        query: str, 
        check_urls: bool = True
    ) -> Optional[Dict]:
        """
        Получить ответ из базы знаний с проверкой URL
        
        Args:
            query: Вопрос пользователя
            check_urls: Проверять ли актуальность URL
            
        Returns:
            Optional[Dict]: Словарь с ответом и метаданными или None
        """
        # Ищем релевантные вопросы
        relevant = self.find_relevant_questions(query, threshold=0.5, top_k=1)
        
        if not relevant:
            logger.debug(f"Релевантные вопросы для '{query}' не найдены")
            return None
        
        # Берем самый релевантный
        best_match, similarity = relevant[0]
        
        # Если схожесть слишком низкая, не возвращаем
        if similarity < 0.3:
            return None
        
        # Проверяем URL, если требуется
        url_valid = None
        url_status = None
        
        if check_urls and best_match.get('legal_url'):
            url_valid, url_status = await self.check_url_validity(best_match['legal_url'])
        
        return {
            'question': best_match['question'],
            'answer': best_match['short_answer'],
            'legal_reference': best_match['legal_reference'],
            'legal_url': best_match['legal_url'],
            'block': best_match['block'],
            'current_as_of': best_match['current_as_of'],
            'similarity_score': similarity,
            'url_valid': url_valid,
            'url_status': url_status
        }
    
    def format_answer_for_user(self, answer_data: Dict) -> str:
        """
        Форматировать ответ для пользователя
        
        Args:
            answer_data: Данные ответа из get_answer_with_validation
            
        Returns:
            str: Отформатированный текст
        """
        text_parts = []
        
        # Заголовок
        text_parts.append(f"📚 <b>Найдено в базе знаний</b>")
        text_parts.append(f"<b>Категория:</b> {answer_data['block']}")
        text_parts.append("")
        
        # Вопрос
        text_parts.append(f"<b>Вопрос:</b> {answer_data['question']}")
        text_parts.append("")
        
        # Ответ
        text_parts.append(f"<b>Ответ:</b> {answer_data['answer']}")
        text_parts.append("")
        
        # Правовая база (только для государственных источников)
        legal_ref = answer_data.get('legal_reference', '')
        legal_url = answer_data.get('legal_url', '')
        
        # Генерируем правильную ссылку на статью ТК РФ
        if legal_ref and 'ТК РФ' in legal_ref:
            # Извлекаем номер статьи из правовой базы
            article_match = self._extract_article_number(legal_ref)
            if article_match:
                correct_url = f"https://www.consultant.ru/document/cons_doc_LAW_34683/{article_match}/"
                text_parts.append(f"<b>Правовая база:</b> {legal_ref}")
                text_parts.append(f"✅ <b>Ссылка:</b> {correct_url}")
            else:
                text_parts.append(f"<b>Правовая база:</b> {legal_ref}")
                text_parts.append(f"<i>ℹ️ Для получения актуальной информации обратитесь к официальным источникам</i>")
        elif legal_url and self._is_government_source(legal_url):
            text_parts.append(f"<b>Правовая база:</b> {legal_ref}")
            url_emoji = "✅" if answer_data.get('url_valid') else "⚠️"
            text_parts.append(f"{url_emoji} <b>Ссылка:</b> {legal_url}")
            
            if answer_data.get('url_valid') is False:
                text_parts.append(f"<i>⚠️ Внимание: ссылка может быть недоступна (код {answer_data.get('url_status', 'N/A')})</i>")
        elif legal_ref:
            # Показываем только правовую базу без ссылки, если ссылка не государственная
            text_parts.append(f"<b>Правовая база:</b> {legal_ref}")
            text_parts.append(f"<i>ℹ️ Для получения актуальной информации обратитесь к официальным источникам</i>")
        else:
            text_parts.append(f"<i>ℹ️ Для получения актуальной информации обратитесь к официальным источникам</i>")
        
        # Актуальность
        text_parts.append("")
        text_parts.append(f"<i>Актуально на: {answer_data['current_as_of']}</i>")
        text_parts.append(f"<i>Степень совпадения: {answer_data['similarity_score']:.0%}</i>")
        
        return "\n".join(text_parts)
    
    def _is_government_source(self, url: str) -> bool:
        """
        Проверить, является ли ссылка государственным источником
        
        Args:
            url: URL для проверки
            
        Returns:
            bool: True если это государственный источник
        """
        if not url:
            return False
        
        # Список государственных доменов
        government_domains = [
            'kremlin.ru',           # Официальный сайт Президента
            'government.ru',        # Правительство РФ
            'duma.gov.ru',          # Государственная Дума
            'council.gov.ru',       # Совет Федерации
            'minjust.gov.ru',       # Минюст
            'mintrud.gov.ru',       # Минтруд
            'rostrud.gov.ru',       # Роструд
            'gks.ru',               # Росстат
            'consultant.ru',        # КонсультантПлюс (работает отлично)
            'pravo.gov.ru',         # Официальный интернет-портал правовой информации
            'fzrf.sudrf.ru',        # Федеральные законы РФ
            'docs.cntd.ru',         # Техэксперт
            'rulaws.ru',            # РУЛАВС
            'zakonrf.info',         # Закон РФ
            'fstec.ru',             # ФСТЭК
            'fsb.ru',               # ФСБ
            'mvd.ru',               # МВД
            'rosgvard.ru',          # Росгвардия
            'gost.ru',              # Росстандарт
            'rospotrebnadzor.ru',   # Роспотребнадзор
            'roszdravnadzor.gov.ru', # Росздравнадзор
            'gost.ru',              # Росстандарт
            'minzdrav.gov.ru',      # Минздрав
            'edu.gov.ru',           # Минобр
            'minobrnauki.gov.ru',   # Минобрнауки
        ]
        
        url_lower = url.lower()
        
        # Проверяем, содержит ли URL государственный домен
        for domain in government_domains:
            if domain in url_lower:
                return True
        
        # Дополнительная проверка на официальные домены .gov.ru
        if '.gov.ru' in url_lower:
            return True
            
        # Проверка на официальные порталы правовой информации
        if any(keyword in url_lower for keyword in ['pravo.gov.ru', 'fzrf.sudrf.ru']):
            return True
        
        return False
    
    def _extract_article_number(self, legal_ref: str) -> str:
        """
        Извлечь номер статьи из правовой базы
        
        Args:
            legal_ref: Правовая база (например, "ТК РФ ст. 209")
            
        Returns:
            str: Номер статьи для URL или пустая строка
        """
        import re
        
        # Ищем паттерн "ст. 209" или "ст.209"
        article_pattern = r'ст\.\s*(\d+(?:\.\d+)?)'
        match = re.search(article_pattern, legal_ref)
        
        if match:
            article_num = match.group(1)
            # Формируем правильный URL для статьи ТК РФ
            return f"st-{article_num}"
        
        return ""
    
    def get_statistics(self) -> Dict:
        """
        Получить статистику по базе знаний
        
        Returns:
            Dict: Статистика
        """
        if not self.faq_data:
            return {
                'total_questions': 0,
                'blocks': [],
                'questions_with_urls': 0,
                'questions_without_urls': 0
            }
        
        blocks = {}
        urls_count = 0
        
        for item in self.faq_data:
            block = item['block']
            blocks[block] = blocks.get(block, 0) + 1
            
            if item.get('legal_url') and item['legal_url'].strip():
                urls_count += 1
        
        return {
            'total_questions': len(self.faq_data),
            'blocks': blocks,
            'questions_with_urls': urls_count,
            'questions_without_urls': len(self.faq_data) - urls_count
        }


# Глобальный экземпляр базы знаний
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """
    Получить глобальный экземпляр базы знаний (singleton)
    
    Returns:
        KnowledgeBase: Экземпляр базы знаний
    """
    global _knowledge_base
    
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    
    return _knowledge_base

