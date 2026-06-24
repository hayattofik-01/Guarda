import { NextResponse } from "next/server";
import { Resend } from "resend";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const { email, name, company } = await request.json();

    if (!email || !name) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    const apiKey = process.env.RESEND_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: "Email service not configured" }, { status: 500 });
    }

    const resend = new Resend(apiKey);

    const { data, error: sendError } = await resend.emails.send({
      from: "Guarda Demo <onboarding@resend.dev>",
      to: "hayattofik22@gmail.com",
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

    if (sendError) {
      console.error("Resend error:", sendError);
      return NextResponse.json({ error: sendError.message }, { status: 500 });
    }

    return NextResponse.json({ success: true, id: data?.id });
  } catch (error) {
    console.error("Email send error:", error);
    return NextResponse.json({ error: "Failed to send email" }, { status: 500 });
  }
}
