using System;
using RosMessageTypes.Std;
using RosMessageTypes.BuiltinInterfaces;

/// <summary>
///     A timer for extended header class 
/// </summary>
public class Timer
{
    public static DateTime UNIX_EPOCH = new DateTime(1970, 1, 1, 0, 0, 0, 0, DateTimeKind.Utc);

    public virtual TimeMsg Now()
    {
        Now(out uint sec, out uint nanosec);
        return new TimeMsg
        {
            sec = (int)sec,
            nanosec = (uint)nanosec
        };
    }

    public virtual void Now(TimeMsg stamp)
    {
        uint sec; uint nanosec;
        Now(out sec, out nanosec);
        stamp.sec = (int)sec;
        stamp.nanosec = nanosec;
    }

    private static void Now(out uint sec, out uint nanosec)
    {
        TimeSpan timeSpan = DateTime.Now.ToUniversalTime() - UNIX_EPOCH;
        double msecs = timeSpan.TotalMilliseconds;
        sec = (uint)(msecs / 1000);
        double seconds = msecs / 1000;
        double fractionalSeconds = seconds - Math.Floor(seconds);
        nanosec = (uint)(fractionalSeconds * 1e9);
    }
}
