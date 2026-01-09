import React, { useState, useEffect } from 'react';
import { rulesetsAPI } from '../services/api';
import RulesetList from './RulesetList';
import RulesetForm from './RulesetForm';

const RulesetManager = () => {
  const [rulesets, setRulesets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingRuleset, setEditingRuleset] = useState(null);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    loadRulesets();
  }, []);

  const loadRulesets = async () => {
    try {
      const rulesetList = await rulesetsAPI.list();
      setRulesets(rulesetList);
    } catch (error) {
      console.error('Failed to load rulesets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingRuleset(null);
    setShowForm(true);
  };

  const handleEdit = (ruleset) => {
    setEditingRuleset(ruleset);
    setShowForm(true);
  };

  const handleDelete = async (rulesetId) => {
    if (!confirm('Are you sure you want to delete this ruleset?')) {
      return;
    }

    try {
      await rulesetsAPI.delete(rulesetId);
      loadRulesets(); // Reload list
    } catch (error) {
      console.error('Failed to delete ruleset:', error);
      alert('Failed to delete ruleset. Please try again.');
    }
  };

  const handleFormSubmit = async (rulesetData) => {
    try {
      if (editingRuleset) {
        await rulesetsAPI.update(editingRuleset.id, rulesetData);
      } else {
        await rulesetsAPI.create(rulesetData);
      }
      setShowForm(false);
      setEditingRuleset(null);
      loadRulesets(); // Reload list
    } catch (error) {
      console.error('Failed to save ruleset:', error);
      alert(error.response?.data?.detail || 'Failed to save ruleset. Please try again.');
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingRuleset(null);
  };

  if (loading) {
    return <div className="loading">Loading rulesets...</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Ruleset Management</h2>
        {!showForm && (
          <button onClick={handleCreate}>Create New Ruleset</button>
        )}
      </div>

      {showForm ? (
        <RulesetForm
          ruleset={editingRuleset}
          onSubmit={handleFormSubmit}
          onCancel={handleCancel}
        />
      ) : (
        <RulesetList
          rulesets={rulesets}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
};

export default RulesetManager;
