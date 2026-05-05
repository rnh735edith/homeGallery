import { useState } from "react";
import { Link } from "react-router-dom";
import { contact } from "../services/api";

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    subject: "",
    message: "",
  });
  const [status, setStatus] = useState("idle");
  const [errors, setErrors] = useState({});

  const validate = () => {
    const newErrors = {};
    if (!formData.name.trim()) newErrors.name = "Name is required";
    if (!formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Invalid email address";
    }
    if (!formData.message.trim()) newErrors.message = "Message is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setStatus("submitting");
    try {
      await contact.submitMessage({
        name: formData.name.trim(),
        email: formData.email.trim(),
        subject: formData.subject.trim() || undefined,
        message: formData.message.trim(),
      });
      setStatus("success");
      setFormData({ name: "", email: "", subject: "", message: "" });
    } catch (err) {
      if (err?.status === 429) {
        setErrors({ form: "Too many submissions. Please try again later." });
      } else {
        setErrors({ form: "Failed to send message. Please try again." });
      }
      setStatus("error");
    }
  };

  if (status === "success") {
    return (
      <div className="contact-page">
        <div className="contact-container">
          <div className="contact-success">
            <h2>Message Sent!</h2>
            <p>Thank you for reaching out. We will get back to you soon.</p>
            <Link to="/" className="contact-back-link">
              Back to Gallery
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="contact-page">
      <div className="contact-container">
        <h1>Contact Us</h1>
        <p className="contact-intro">
          Have a question, feedback, or feature request? Fill out the form below
          and we will get back to you.
        </p>

        {errors.form && <div className="contact-error">{errors.form}</div>}

        <form onSubmit={handleSubmit} className="contact-form" noValidate>
          <div className="form-group">
            <label htmlFor="name">Name *</label>
            <input
              id="name"
              name="name"
              type="text"
              value={formData.name}
              onChange={handleChange}
              className={errors.name ? "input-error" : ""}
              placeholder="Your name"
            />
            {errors.name && <span className="field-error">{errors.name}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="email">Email *</label>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              className={errors.email ? "input-error" : ""}
              placeholder="your@email.com"
            />
            {errors.email && (
              <span className="field-error">{errors.email}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="subject">Subject</label>
            <input
              id="subject"
              name="subject"
              type="text"
              value={formData.subject}
              onChange={handleChange}
              placeholder="What is this about?"
            />
          </div>

          <div className="form-group">
            <label htmlFor="message">Message *</label>
            <textarea
              id="message"
              name="message"
              rows="5"
              value={formData.message}
              onChange={handleChange}
              className={errors.message ? "input-error" : ""}
              placeholder="Your message..."
            />
            {errors.message && (
              <span className="field-error">{errors.message}</span>
            )}
          </div>

          <button
            type="submit"
            className="contact-submit-btn"
            disabled={status === "submitting"}
          >
            {status === "submitting" ? "Sending..." : "Send Message"}
          </button>
        </form>

        <div className="contact-footer">
          <p>
            Or{" "}
            <Link to="/about" className="contact-link">
              learn more about HomeGallery
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
