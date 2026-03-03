import React from 'react';
import '../styles/components/TopicSuggestions.css';

/**
 * TopicSuggestions
 *
 * Renders a ranked grid of LLM-generated topic suggestions.
 * Each card shows rank, topic, rationale, and a virality-score bar.
 *
 * Props:
 *   topics        – array of { rank, topic, rationale, score }
 *   loading       – boolean — show skeleton cards while fetching
 *   error         – string | null — error message to display
 *   trendsAnalysed – number of trend videos fed to the LLM
 *   onSelectTopic – callback(topic: string) when user clicks a card
 *   niche         – the niche string used (for subtitle)
 */
const TopicSuggestions = ({
    topics = [],
    loading = false,
    error = null,
    trendsAnalysed = 0,
    onSelectTopic,
    niche = '',
}) => {
    const scoreColor = (score) => {
        if (score >= 80) return 'var(--score-high)';
        if (score >= 60) return 'var(--score-mid)';
        return 'var(--score-low)';
    };

    const rankEmoji = (rank) => {
        const medals = ['🥇', '🥈', '🥉'];
        return medals[rank - 1] || `#${rank}`;
    };

    // ── Loading skeleton ─────────────────────────────────────────────────────
    if (loading) {
        return (
            <div className="topic-suggestions">
                <div className="ts-header">
                    <h3 className="ts-title">
                        <span className="ts-sparkle">✨</span> Generating Topic Suggestions…
                    </h3>
                    <p className="ts-subtitle">Analysing trending content for <strong>{niche}</strong></p>
                </div>
                <div className="ts-grid">
                    {Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="ts-card ts-card--skeleton">
                            <div className="skeleton-rank" />
                            <div className="skeleton-title" />
                            <div className="skeleton-rationale" />
                            <div className="skeleton-bar" />
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    // ── Error state ───────────────────────────────────────────────────────────
    if (error) {
        return (
            <div className="topic-suggestions">
                <div className="ts-header">
                    <h3 className="ts-title">
                        <span className="ts-sparkle">✨</span> AI Topic Suggestions
                    </h3>
                </div>
                <div className="ts-error">
                    <span>⚠️</span>
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    // ── Empty state ───────────────────────────────────────────────────────────
    if (!loading && topics.length === 0) {
        return (
            <div className="topic-suggestions">
                <div className="ts-header">
                    <h3 className="ts-title">
                        <span className="ts-sparkle">✨</span> AI Topic Suggestions
                    </h3>
                    <p className="ts-subtitle">No suggestions available. Try a different niche.</p>
                </div>
            </div>
        );
    }

    // ── Suggestions grid ──────────────────────────────────────────────────────
    return (
        <div className="topic-suggestions">
            <div className="ts-header">
                <h3 className="ts-title">
                    <span className="ts-sparkle">✨</span> AI Topic Suggestions
                </h3>
                <p className="ts-subtitle">
                    Based on <strong>{trendsAnalysed}</strong> high-engagement Shorts in{' '}
                    <strong>{niche}</strong> — click any card to use it as your topic
                </p>
            </div>

            <div className="ts-grid">
                {topics.map((item) => (
                    <div
                        key={item.rank}
                        className="ts-card"
                        onClick={() => onSelectTopic && onSelectTopic(item.topic)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => e.key === 'Enter' && onSelectTopic && onSelectTopic(item.topic)}
                        aria-label={`Select topic: ${item.topic}`}
                    >
                        {/* Rank badge */}
                        <div className="ts-rank-badge">{rankEmoji(item.rank)}</div>

                        {/* Topic title */}
                        <h4 className="ts-topic">{item.topic}</h4>

                        {/* Rationale */}
                        <p className="ts-rationale">{item.rationale}</p>

                        {/* Virality score bar */}
                        <div className="ts-score-section">
                            <span className="ts-score-label">Virality Score</span>
                            <div className="ts-score-bar-bg">
                                <div
                                    className="ts-score-bar-fill"
                                    style={{
                                        width: `${item.score}%`,
                                        background: `linear-gradient(90deg, ${scoreColor(item.score)}, ${scoreColor(item.score)}cc)`,
                                    }}
                                />
                            </div>
                            <span className="ts-score-value" style={{ color: scoreColor(item.score) }}>
                                {item.score}
                            </span>
                        </div>

                        <div className="ts-select-hint">Click to select →</div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TopicSuggestions;
