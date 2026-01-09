import React, { useState, useEffect } from 'react';

const RulesetForm = ({ ruleset, onSubmit, onCancel }) => {
  const [name, setName] = useState('');
  const [keywords, setKeywords] = useState('');
  const [description, setDescription] = useState('');
  const [minYear, setMinYear] = useState('');
  const [maxYear, setMaxYear] = useState('');
  const [yearsBack, setYearsBack] = useState('');
  const [genreFilter, setGenreFilter] = useState('');
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    if (ruleset) {
      setName(ruleset.name || '');
      setKeywords(ruleset.keywords ? ruleset.keywords.join(', ') : '');
      setDescription(ruleset.description || '');
      setMinYear(ruleset.criteria?.min_year?.toString() || '');
      setMaxYear(ruleset.criteria?.max_year?.toString() || '');
      setYearsBack(ruleset.criteria?.years_back?.toString() || '');
      setGenreFilter(
        ruleset.criteria?.genre_filter && Array.isArray(ruleset.criteria.genre_filter)
          ? ruleset.criteria.genre_filter.join(', ')
          : ''
      );
      setIsActive(ruleset.is_active !== false);
    }
  }, [ruleset]);

  const handleSubmit = (e) => {
    e.preventDefault();

    // Parse keywords
    const keywordList = keywords
      .split(',')
      .map((k) => k.trim())
      .filter((k) => k.length > 0);

    if (keywordList.length === 0) {
      alert('Please enter at least one keyword');
      return;
    }

    // Build criteria object
    const criteria = {};
    if (minYear) {
      criteria.min_year = parseInt(minYear);
    }
    if (maxYear) {
      criteria.max_year = parseInt(maxYear);
    }
    if (yearsBack) {
      criteria.years_back = parseInt(yearsBack);
    }
    if (genreFilter.trim()) {
      criteria.genre_filter = genreFilter
        .split(',')
        .map((g) => g.trim())
        .filter((g) => g.length > 0);
    }

    const rulesetData = {
      name: name.trim(),
      keywords: keywordList,
      description: description.trim() || undefined,
      criteria,
      is_active: isActive,
    };

    onSubmit(rulesetData);
  };

  return (
    <form onSubmit={handleSubmit} className="card">
      <h3>{ruleset ? 'Edit Ruleset' : 'Create New Ruleset'}</h3>

      <div className="form-group">
        <label htmlFor="name">Name *</label>
        <input
          type="text"
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., throwback, fresh"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="keywords">Keywords * (comma-separated)</label>
        <input
          type="text"
          id="keywords"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          placeholder="e.g., throwback, retro, oldies"
          required
        />
        <small style={{ color: '#666', marginTop: '5px', display: 'block' }}>
          These keywords will trigger this ruleset when found in playlist guidelines
        </small>
      </div>

      <div className="form-group">
        <label htmlFor="description">Description</label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Human-readable description of this ruleset"
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px', marginBottom: '20px' }}>
        <div className="form-group">
          <label htmlFor="minYear">Min Year</label>
          <input
            type="number"
            id="minYear"
            value={minYear}
            onChange={(e) => setMinYear(e.target.value)}
            placeholder="e.g., 2000"
            min="1900"
            max={new Date().getFullYear()}
          />
        </div>

        <div className="form-group">
          <label htmlFor="maxYear">Max Year</label>
          <input
            type="number"
            id="maxYear"
            value={maxYear}
            onChange={(e) => setMaxYear(e.target.value)}
            placeholder="e.g., 2010"
            min="1900"
            max={new Date().getFullYear()}
          />
        </div>

        <div className="form-group">
          <label htmlFor="yearsBack">Years Back</label>
          <input
            type="number"
            id="yearsBack"
            value={yearsBack}
            onChange={(e) => setYearsBack(e.target.value)}
            placeholder="e.g., 5"
            min="1"
          />
          <small style={{ color: '#666', marginTop: '5px', display: 'block' }}>
            Minimum year = current year - this value
          </small>
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="genreFilter">Genre Filter (comma-separated)</label>
        <input
          type="text"
          id="genreFilter"
          value={genreFilter}
          onChange={(e) => setGenreFilter(e.target.value)}
          placeholder="e.g., rock, pop, jazz"
        />
      </div>

      <div className="form-group">
        <div className="checkbox-group">
          <input
            type="checkbox"
            id="isActive"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          <label htmlFor="isActive" style={{ marginBottom: 0 }}>
            Active (ruleset will be used for matching)
          </label>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        <button type="submit">{ruleset ? 'Update' : 'Create'} Ruleset</button>
        <button type="button" onClick={onCancel} className="secondary">
          Cancel
        </button>
      </div>
    </form>
  );
};

export default RulesetForm;
