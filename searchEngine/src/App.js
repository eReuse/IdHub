import React from 'react';
import { BrowserRouter as Router, Route } from 'react-router-dom';
import SearchPage from './SearchPage';
import SearchResultsPage from './SearchResultsPage';
import SearchResultsPageDeep from './SearchResultsPageDeep';
import 'bootstrap/dist/css/bootstrap.min.css';
import "./App.css"

const App = () => {
  return (
    <Router>
      <Route exact path="/" component={SearchPage} />
      <Route path="/search" component={SearchResultsPage} />
      <Route path="/deepSearch" component={SearchResultsPageDeep} />
    </Router>
  );
};

export default App;