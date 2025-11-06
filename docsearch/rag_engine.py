"""
DocSearch - RAG Engine (Retrieval Augmented Generation)
Genera risposte intelligenti con percorsi/flussi di documentazione
"""

import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SearchContext:
    """Contesto di ricerca"""
    query: str
    results: List[Dict]
    total_results: int


class RAGEngine:
    """
    Motore RAG per risposte intelligenti
    Può usare OpenAI API o generare risposte basate su regole
    """

    def __init__(self, use_openai: bool = False, api_key: Optional[str] = None):
        """
        Inizializza RAG Engine

        Args:
            use_openai: Se True, usa OpenAI API per risposte più intelligenti
            api_key: OpenAI API key (opzionale)
        """
        self.use_openai = use_openai
        self.openai_client = None

        if use_openai:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
                logger.info("✅ OpenAI API enabled")
            except Exception as e:
                logger.warning(f"⚠️  OpenAI not available: {e}")
                self.use_openai = False

    def generate_answer(self, search_context: SearchContext) -> Dict:
        """
        Genera una risposta intelligente basata sui risultati di ricerca

        Args:
            search_context: Contesto con query e risultati

        Returns:
            {
                'answer': str,              # Risposta principale
                'confidence': float,        # Confidenza della risposta (0-1)
                'sources': List[Dict],      # Fonti utilizzate
                'flow': List[str],          # Flusso/percorso per arrivare all'info
                'suggestions': List[str]    # Suggerimenti per ricerche correlate
            }
        """
        if not search_context.results:
            return self._generate_no_results_response(search_context.query)

        if self.use_openai and self.openai_client:
            return self._generate_openai_answer(search_context)
        else:
            return self._generate_rule_based_answer(search_context)

    def _generate_openai_answer(self, context: SearchContext) -> Dict:
        """Genera risposta usando OpenAI API"""
        try:
            # Prepara contesto per OpenAI
            documents_text = self._prepare_context_for_llm(context.results)

            # Prompt ottimizzato
            prompt = f"""Sei un assistente intelligente per la ricerca documentale.
Hai accesso a questi documenti rilevanti:

{documents_text}

Domanda dell'utente: {context.query}

Fornisci una risposta completa che:
1. Risponda direttamente alla domanda
2. Citi i documenti specifici utilizzati
3. Suggerisca un flusso/percorso per approfondire l'argomento
4. Proponga ricerche correlate utili

Formato della risposta:
RISPOSTA: [la tua risposta dettagliata]
FLUSSO: [step1 -> step2 -> step3]
SUGGERIMENTI: [suggerimento1, suggerimento2, suggerimento3]
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sei un assistente esperto per la ricerca documentale."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )

            answer_text = response.choices[0].message.content

            # Parse risposta
            parsed = self._parse_openai_response(answer_text)

            return {
                'answer': parsed['answer'],
                'confidence': 0.85,
                'sources': self._extract_sources(context.results[:3]),
                'flow': parsed['flow'],
                'suggestions': parsed['suggestions']
            }

        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            # Fallback a rule-based
            return self._generate_rule_based_answer(context)

    def _generate_rule_based_answer(self, context: SearchContext) -> Dict:
        """
        Genera risposta basata su regole (senza OpenAI)
        """
        query = context.query.lower()
        results = context.results
        top_result = results[0] if results else None

        # Analizza il tipo di domanda
        question_type = self._detect_question_type(query)

        # Genera risposta
        answer_parts = []

        if question_type == 'how':
            answer_parts.append(f"Per quanto riguarda '{context.query}', ho trovato {len(results)} documenti rilevanti.")
        elif question_type == 'what':
            answer_parts.append(f"Riguardo a '{context.query}', ecco cosa ho trovato:")
        elif question_type == 'where':
            answer_parts.append(f"La risposta a '{context.query}' si trova in questi documenti:")
        else:
            answer_parts.append(f"Ho trovato {len(results)} documenti che potrebbero rispondere alla tua domanda.")

        # Aggiungi info dal documento più rilevante
        if top_result:
            answer_parts.append(f"\n\n📄 **Documento principale**: {top_result['filename']}")

            if top_result.get('highlight'):
                answer_parts.append(f"\n{top_result['highlight']}")
            elif top_result.get('summary'):
                answer_parts.append(f"\n{top_result['summary'][:300]}...")

            # Keywords rilevanti
            if top_result.get('keywords'):
                keywords = ', '.join(top_result['keywords'][:5])
                answer_parts.append(f"\n\n🔑 **Concetti chiave**: {keywords}")

        # Genera flusso
        flow = self._generate_exploration_flow(results, question_type)

        # Genera suggerimenti
        suggestions = self._generate_suggestions(context.query, results)

        return {
            'answer': ''.join(answer_parts),
            'confidence': self._calculate_confidence(results),
            'sources': self._extract_sources(results[:3]),
            'flow': flow,
            'suggestions': suggestions
        }

    def _generate_no_results_response(self, query: str) -> Dict:
        """Risposta quando non ci sono risultati"""
        suggestions = [
            f"Prova a cercare con termini più generici",
            f"Verifica l'ortografia di '{query}'",
            f"Cerca parole chiave singole invece di frasi complete"
        ]

        return {
            'answer': f"😕 Non ho trovato documenti per '{query}'.\n\nProva a riformulare la ricerca o usa termini diversi.",
            'confidence': 0.0,
            'sources': [],
            'flow': [],
            'suggestions': suggestions
        }

    def _detect_question_type(self, query: str) -> str:
        """Rileva il tipo di domanda"""
        query_lower = query.lower()

        if any(word in query_lower for word in ['come', 'how']):
            return 'how'
        elif any(word in query_lower for word in ['cosa', 'che cosa', 'what']):
            return 'what'
        elif any(word in query_lower for word in ['dove', 'where']):
            return 'where'
        elif any(word in query_lower for word in ['perché', 'why']):
            return 'why'
        elif any(word in query_lower for word in ['quando', 'when']):
            return 'when'
        else:
            return 'general'

    def _generate_exploration_flow(self, results: List[Dict], question_type: str) -> List[str]:
        """
        Genera un flusso di esplorazione per approfondire l'argomento
        """
        flow = []

        if not results:
            return flow

        # Step 1: Documento principale
        top_doc = results[0]
        flow.append(f"1. 📖 Inizia con: {top_doc['filename']}")

        # Step 2: Documenti correlati
        if len(results) > 1:
            related_docs = [r['filename'] for r in results[1:3]]
            if related_docs:
                flow.append(f"2. 🔗 Approfondisci con: {', '.join(related_docs)}")

        # Step 3: Concetti chiave
        all_keywords = []
        for r in results[:3]:
            all_keywords.extend(r.get('keywords', []))

        # Prendi keywords più comuni
        keyword_freq = {}
        for kw in all_keywords:
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1

        top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:3]

        if top_keywords:
            keywords_str = ', '.join([kw for kw, _ in top_keywords])
            flow.append(f"3. 🎯 Esplora i concetti: {keywords_str}")

        # Step 4: Documenti per tipo
        doc_types = {}
        for r in results:
            doc_type = r['type']
            if doc_type not in doc_types:
                doc_types[doc_type] = []
            doc_types[doc_type].append(r['filename'])

        if len(doc_types) > 1:
            types_str = ', '.join(doc_types.keys())
            flow.append(f"4. 📑 Consulta anche: {types_str}")

        return flow

    def _generate_suggestions(self, query: str, results: List[Dict]) -> List[str]:
        """Genera suggerimenti per ricerche correlate"""
        suggestions = []

        # Suggerimenti basati su keywords
        all_keywords = []
        for r in results[:5]:
            all_keywords.extend(r.get('keywords', []))

        # Keywords più frequenti
        keyword_freq = {}
        for kw in all_keywords:
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1

        top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:5]

        for kw, _ in top_keywords[:3]:
            if kw.lower() not in query.lower():
                suggestions.append(f"Cerca anche: {kw}")

        # Suggerimenti per tipo documento
        doc_types = set(r['type'] for r in results)
        for doc_type in doc_types:
            if len([r for r in results if r['type'] == doc_type]) > 1:
                suggestions.append(f"Filtra per: {doc_type}")

        return suggestions[:5]

    def _extract_sources(self, results: List[Dict]) -> List[Dict]:
        """Estrae le fonti dai risultati"""
        sources = []

        for r in results:
            sources.append({
                'filename': r['filename'],
                'type': r['type'],
                'score': round(r['score'], 2),
                'path': r.get('file_path', '')
            })

        return sources

    def _calculate_confidence(self, results: List[Dict]) -> float:
        """Calcola confidenza della risposta"""
        if not results:
            return 0.0

        # Basato su score del primo risultato
        top_score = results[0]['score']

        # Normalizza (score tipici: 1-20)
        confidence = min(top_score / 20.0, 1.0)

        # Boost se ci sono più risultati rilevanti
        if len(results) >= 3:
            confidence = min(confidence * 1.2, 1.0)

        return round(confidence, 2)

    def _prepare_context_for_llm(self, results: List[Dict]) -> str:
        """Prepara contesto per LLM"""
        context_parts = []

        for i, result in enumerate(results[:3], 1):
            context_parts.append(f"\n--- Documento {i}: {result['filename']} ---")

            if result.get('highlight'):
                context_parts.append(result['highlight'])
            elif result.get('summary'):
                context_parts.append(result['summary'])

        return '\n'.join(context_parts)

    def _parse_openai_response(self, response_text: str) -> Dict:
        """Parse risposta OpenAI"""
        answer = response_text
        flow = []
        suggestions = []

        # Cerca sezioni
        lines = response_text.split('\n')
        current_section = 'answer'
        answer_lines = []
        flow_lines = []
        suggestion_lines = []

        for line in lines:
            line_upper = line.upper().strip()

            if 'FLUSSO:' in line_upper or 'FLOW:' in line_upper:
                current_section = 'flow'
                continue
            elif 'SUGGERIMENT' in line_upper or 'SUGGESTION' in line_upper:
                current_section = 'suggestions'
                continue
            elif 'RISPOSTA:' in line_upper or 'ANSWER:' in line_upper:
                current_section = 'answer'
                continue

            if current_section == 'answer':
                answer_lines.append(line)
            elif current_section == 'flow':
                if line.strip():
                    flow_lines.append(line.strip())
            elif current_section == 'suggestions':
                if line.strip():
                    suggestion_lines.append(line.strip())

        return {
            'answer': '\n'.join(answer_lines).strip(),
            'flow': flow_lines if flow_lines else ['Consulta i documenti trovati'],
            'suggestions': suggestion_lines[:5] if suggestion_lines else []
        }


# Test
if __name__ == '__main__':
    # Mock search results
    mock_results = [
        {
            'filename': 'guida_opensearch.pdf',
            'type': 'PDF Document',
            'score': 15.5,
            'summary': 'Guida completa all\'installazione di OpenSearch...',
            'keywords': ['opensearch', 'installazione', 'configurazione'],
            'highlight': 'OpenSearch è un motore di ricerca distribuito...'
        },
        {
            'filename': 'tutorial_python.md',
            'type': 'Markdown Document',
            'score': 12.3,
            'summary': 'Tutorial Python per lavorare con OpenSearch...',
            'keywords': ['python', 'opensearch', 'api'],
            'highlight': 'Per connettersi a OpenSearch usa opensearch-py...'
        }
    ]

    context = SearchContext(
        query='Come installare OpenSearch?',
        results=mock_results,
        total_results=2
    )

    rag = RAGEngine(use_openai=False)
    response = rag.generate_answer(context)

    print("\n🤖 RAG Response:")
    print(f"\nAnswer:\n{response['answer']}")
    print(f"\nConfidence: {response['confidence']}")
    print(f"\nFlow:")
    for step in response['flow']:
        print(f"  {step}")
    print(f"\nSuggestions:")
    for sug in response['suggestions']:
        print(f"  - {sug}")
