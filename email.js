require('dotenv').config();
const nodemailer = require('nodemailer');

// Configure Zoho SMTP transporter
const transporter = nodemailer.createTransport({
    host: 'smtp.zoho.com',
    port: 587,
    secure: true,
    auth: {
        user: 'qotiba@zohomail.com',  // Your Zoho email
        pass: 'mjDhkBqvVkiW',         // Your Zoho App Password
    },
});

// Email details
const mailOptions = {
    from: 'qotiba@zohomail.com',  
    to: 'qotibaeiad11@gmail.com',  
    subject: 'Test Email from Zoho SMTP',
    text: 'This is a test email to confirm that SMTP is working!',
};

// Send email
transporter.sendMail(mailOptions, (error, info) => {
    if (error) {
        console.error('Error sending email:', error);
    } else {
        console.log('Email sent successfully:', info.response);
    }
});
