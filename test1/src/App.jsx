import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [name, setName] = useState('');
  const [reviews, setReviews] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');  // Add a state for error handling

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSummary(null);
    setReviews(null);
    setLoading(true);
    setProgress(0);
    setError('');  // Reset error message

    // Simulate loading progress
    const simulateProgress = () => {
      setProgress(prevProgress => {
        if (prevProgress < 75) {
          return prevProgress + 5; // Increase faster when below 75
        } else if (prevProgress < 99) {
          return prevProgress + 1; // Slow down as it approaches 99
        } else {
          return 99; // Ensure it doesn't exceed 99
        }
      });
    };

    const progressInterval = setInterval(simulateProgress, 1250); // Update progress every 1.25 seconds

    try {
      const reviewResponse = await axios.post('https://profratingsbackend.onrender.com/api/reviews', { name });
      console.log('Reviews Response:', reviewResponse.data);

      if (reviewResponse.data.reviews.length === 0) {
        setError('No professor found');  // Set error message if reviews are empty
      } else {
        setReviews(reviewResponse.data.reviews);
        
        const summaryResponse = await axios.post('https://profratingsbackend.onrender.com/api/summary', { reviews: reviewResponse.data.reviews });
        console.log('Summary Response:', summaryResponse.data);
        setSummary(summaryResponse.data);
      }
    } catch (error) {
      console.error("There was an error fetching the data!", error);
      setError('An error occurred while fetching data.');
    } finally {
      clearInterval(progressInterval); // Stop the interval when the request is completed
      setProgress(100);  // Ensure progress bar reaches 100%
      setTimeout(() => setLoading(false), 500);  // Add slight delay before hiding the loading bar
    }
  };

  return (
    <div className="Website">
      <div className="container">
        <div className="container" style={{ textAlign: 'center', gap: '10px', alignItems: 'center' }}>
          <h1 style={{ width: '100%', textAlign: 'center' }}>Professor Reviews</h1>
          <form onSubmit={handleSubmit}>
            <input
              style={{ marginRight: '10px', padding: '10px' }}
              type="text"
              placeholder="Enter professor's name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <button style={{ marginTop: '10px', padding: '10px' }} type="submit">Get Summary</button>
          </form>
          {loading && (
            <div style={{ marginTop: '10px', width: '50%', textAlign: 'center', alignItems: 'center', 
            justifyContent: 'center', margin: '0 auto'}}>
              <progress value={progress} max="100" style={{ width: '100%', height: '40px' }}></progress>
              <span>{progress}%</span>
            </div>
          )}
          {error && <p style={{ color: 'red' }}>{error}</p>}  {/* Display error message */}
        </div>
        {!loading && summary && (
          <div className="container" style={{ padding: '0px 250px', textAlign: 'left' }}>
            <h2 style={{ textAlign: "center" }}>Summary</h2>
            <div style={{ paddingBottom: '20px' }}>
              <strong>Rating:</strong>
              <span>{summary["Overall Rating"]}</span>
            </div>
            <div>
              <strong>Pros:</strong>
              <ul>
                {summary.Pros.filter(pro => pro).map((pro, index) => <li key={index}>{pro}</li>)}
              </ul>
            </div>
            <div>
              <strong>Cons:</strong>
              <ul>
                {summary.Cons.filter(con => con).map((con, index) => <li key={index}>{con}</li>)}
              </ul>
            </div>
            <div>
              <strong>Specific Feedback:</strong>
              <ul>
                {summary["Specific Feedback"].filter(feedback => feedback).map((feedback, index) => <li key={index}>{feedback}</li>)}
              </ul>
            </div>
            <div>
              <strong>Recommendations:</strong>
              <ul>
                {summary.Recommendations.filter(rec => rec).map((rec, index) => <li key={index}>{rec}</li>)}
              </ul>
            </div>
            <div style={{ paddingBottom: '20px' }}>
              <strong>Overall Summary:</strong> {summary["Overall Summary"]}
            </div>
            <div>
              <strong>Alternative Professor:</strong> {summary["Alternative Professor"]}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
