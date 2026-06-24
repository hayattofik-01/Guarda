import { NextResponse } from "next/server";
import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

export async function POST(request: Request) {
  try {
    const { email, name, company } = await request.json();

    if (!email || !name) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    await resend.emails.send({
      from: "Guarda Demo <onboarding@resend.dev>",
      to: "hayatttofik22@gmail.com",
      subject: `New Demo Request from ${name}`,
      html: `
        <h2>New Demo Booking</h2>
        <p><strong>Name:</strong> ${name}</p>
        <p><strong>Email:</strong> ${email}</p>
        <p><strong>Company/Domain:</strong> ${company || "Not provided"}</p>
        <hr />
        <p>Reply directly to this person at <a href="mailto:${email}">${email}</a></p>
      `,
      replyTo: email,
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Email send error:", error);
    return NextResponse.json({ error: "Failed to send email" }, { status: 500 });
  }
}
