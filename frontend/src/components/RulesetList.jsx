import React from 'react';

const RulesetList = ({ rulesets, onEdit, onDelete }) => {
  if (rulesets.length === 0) {
    return (
      <div className="info">
        No rulesets defined yet. Create your first ruleset to get started.
      </div>
    );
  }

  return (
    <div className="ruleset-list">
      {rulesets.map((ruleset) => (
        <div
          key={ruleset.id}
          className={`ruleset-card ${!ruleset.is_active ? 'inactive' : ''}`}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h3>
                {ruleset.name}
                {!ruleset.is_active && (
                  <span style={{ marginLeft: '10px', color: '#666', fontSize: '0.9em' }}>
                    (Inactive)
                  </span>
                )}
              </h3>
              {ruleset.description && (
                <p style={{ color: '#b3b3b3', marginBottom: '10px' }}>{ruleset.description}</p>
              )}
            </div>
            <div className="ruleset-actions">
              <button onClick={() => onEdit(ruleset)} className="secondary" style={{ fontSize: '0.9em' }}>
                Edit
              </button>
              <button
                onClick={() => onDelete(ruleset.id)}
                className="danger"
                style={{ fontSize: '0.9em' }}
              >
                Delete
              </button>
            </div>
          </div>

          <div style={{ marginTop: '15px' }}>
            <div style={{ marginBottom: '10px' }}>
              <strong>Keywords:</strong>
              <div style={{ marginTop: '5px' }}>
                {ruleset.keywords.map((keyword) => (
                  <span key={keyword} className="keyword-tag">{keyword}</span>
                ))}
              </div>
            </div>

            <div>
              <strong>Criteria:</strong>
              <div style={{ marginTop: '5px', color: '#b3b3b3', fontSize: '0.9em' }}>
                {ruleset.criteria?.max_year && (
                  <div>Max Year: {ruleset.criteria.max_year}</div>
                )}
                {ruleset.criteria?.min_year && (
                  <div>Min Year: {ruleset.criteria.min_year}</div>
                )}
                {ruleset.criteria?.years_back && (
                  <div>Years Back: {ruleset.criteria.years_back}</div>
                )}
                {ruleset.criteria?.genre_filter && Array.isArray(ruleset.criteria.genre_filter) && ruleset.criteria.genre_filter.length > 0 && (
                  <div>
                    Genre Filter: {ruleset.criteria.genre_filter.join(', ')}
                  </div>
                )}
                {(!ruleset.criteria || Object.keys(ruleset.criteria).length === 0) && (
                  <div>No specific criteria defined</div>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default RulesetList;
