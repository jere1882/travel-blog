import { useState } from 'react';
import './ImageCarousel.css';

interface ImageItem {
  src: string;
  alt: string;
  caption?: string;
}

interface ImageCarouselProps {
  images: ImageItem[];
}

export default function ImageCarousel({ images }: ImageCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  const next = () => {
    setCurrentIndex((prev) => (prev + 1) % images.length);
  };

  const prev = () => {
    setCurrentIndex((prev) => (prev - 1 + images.length) % images.length);
  };

  const goToSlide = (index: number) => {
    setCurrentIndex(index);
  };

  if (images.length === 0) return null;

  return (
    <div className="image-carousel">
      <div className="carousel-container">
        {images.length > 1 && (
          <button className="carousel-btn carousel-btn-prev" onClick={prev} aria-label="Previous">
            ‹
          </button>
        )}
        
        <div className="carousel-slide">
          <img 
            src={images[currentIndex].src} 
            alt={images[currentIndex].alt}
            loading="lazy"
          />
          {images[currentIndex].caption && (
            <p className="carousel-caption">{images[currentIndex].caption}</p>
          )}
        </div>
        
        {images.length > 1 && (
          <button className="carousel-btn carousel-btn-next" onClick={next} aria-label="Next">
            ›
          </button>
        )}
      </div>
      
      {images.length > 1 && (
        <>
          <div className="carousel-dots">
            {images.map((_, index) => (
              <button
                key={index}
                className={`carousel-dot ${index === currentIndex ? 'active' : ''}`}
                onClick={() => goToSlide(index)}
                aria-label={`Go to slide ${index + 1}`}
              />
            ))}
          </div>
          
          <div className="carousel-counter">
            {currentIndex + 1} / {images.length}
          </div>
        </>
      )}
    </div>
  );
}

