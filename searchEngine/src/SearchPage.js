import React, { useState } from 'react';
import { Container, Row, Col, Form, Button } from 'react-bootstrap';
import { useHistory } from 'react-router-dom';
// import "./App.css"

const SearchPage = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const history = useHistory();

  const handleSearch = (e) => {
    e.preventDefault();
    // Implement your search logic here
    // For simplicity, we will just navigate to the search results page with the query as a parameter
    history.push(`/search?q=${searchQuery}`);
  };

  return (
    <Container className="mt-5">
      <Row className="justify-content-center">
        <Col md={6}>
          <h1 className="text-center mb-4">DPP Search Engine</h1>
          <Form onSubmit={handleSearch}>
            <Form.Group controlId="searchQuery">
              <Form.Control
                type="text"
                placeholder="Enter your search query"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </Form.Group>
            <Button variant="primary" type="submit" block>
              Search
            </Button>
          </Form>
        </Col>
      </Row>
    </Container>
  );
};

export default SearchPage;
